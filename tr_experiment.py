import pandas as pd
import requests
import random
import re
import os
import argparse

import torch
# Transformers
from transformers import (
    AutoTokenizer, 
    pipeline,
    set_seed,
    logging
)

# Seed for random states
seed= 42
rng = random.Random(seed)

logging.set_verbosity_error()
set_seed(seed)

# Some models use chat template, others not. Define here which ones do.
chat_template= { "model_x": True}


def extract_clean_response(text: str) -> str | None:
    """
    Extract the first occurrence of “A)”, “B)”, or “C)” from the text.
    Return “A)”, “B)”, or “C)” if found, or None if not found.
    """
    pattern = r'(?:^|\s)([ABC]\))'   
    matches = re.findall(pattern, text)
    if matches:
        return matches[-1]  # última coincidencia
    else:
        return None

def extract_noisy_response(text: str) -> str | None:
    """
    Extract the first standalone letter “A”, “B”, or “C” in the text, without parentheses, 
    possibly preceded and/or followed by spaces or line breaks.

    Return “A)”, “B)”, or “C)” if found, or None if not found.
    """
    pattern = r'(?:^|\s)([ABC])(?:\s|$)'   
    matches = re.findall(pattern, text)
    if matches:
        return f"{matches[-1]})"  # última coincidencia
    else:
        return None
    
def extract_response(text:str) -> str | None:
    response= extract_clean_response(text)
    if not response: response= extract_noisy_response(text)
    return response

def render_prompt_for_model(user_prompt: str, pretrained_model_name:str, tokenizer) -> str:
    """If the model uses a chat template, apply it; otherwise, return the prompt as is."""
    if chat_template.get(pretrained_model_name):
        # Define here the chat template structure
        messages = [
            {"role": "system", "content": "You are a chatbot that has to perform temporal reasoning tasks."},
            {"role": "user", "content": user_prompt},
        ]
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        return user_prompt



def temporal_reasoning_experiment(benchmark, benchmark_name, pretrained_model_name, task_types, BATCH_SIZE = 256):
    _benchmark= benchmark.copy()
    # Load tokenizer and model
    tokenizer= AutoTokenizer.from_pretrained(pretrained_model_name)
    # For GPT-2: set pad_token if not exist
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token  # pad = eos (patrón habitual)

    # Longitud máxima de contexto del modelo (viene del tokenizer)
    model_max_length = getattr(tokenizer, "model_max_length", 1024)
    model_max_length = min(model_max_length, 32768)
    
    # Crear el pipeline de generación de texto
    pipe = pipeline(
        "text-generation", 
        model=pretrained_model_name, 
        tokenizer=tokenizer,
        torch_dtype="auto", 
        device_map="auto",
        truncation=True,
        model_kwargs={
            "attn_implementation": "eager",  # mismo truco que en tu script largo
        }
    )

    # Generación capada: sin apenas margen
    max_new_tokens= 10
    limited_gen_cfg = dict(
        do_sample=False,           # determinista para evaluación; cambia a True si quieres CoT más diverso
        max_new_tokens=max_new_tokens,         # margen corto para no razonar
        min_new_tokens=1,         # evita cortes prematuros
        return_full_text=False,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id
        )

    max_input_tokens = model_max_length - max_new_tokens

    print(f"CUDA available: {torch.cuda.is_available()}", flush=True)
    print(f"GPU in use: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}", flush=True)
    print(f"Model used: {pretrained_model_name}")
    print(f"Pipeline device: {pipe.device}", flush=True)

    OUT_CSV= f"benchmark_{benchmark_name}_{pretrained_model_name.split('/')[-1]}"
    

    # Cargamos las columnas de las tareas terminadas, así evitamos repetir tareas
    if os.path.exists(f"{OUT_CSV}.csv"):
        benchmark_bak = pd.read_csv(f"{OUT_CSV}.csv")
        for col in benchmark_bak.columns:
            if col not in _benchmark.columns:
                _benchmark[col] = benchmark_bak[col]

    for task_type in task_types:
        column= f"target_{task_type}" # nombre de la columna en el dataset que tendra los resultados de la tarea
        chk_point = f"{OUT_CSV}_bak_{column}" # nombre del fichero de checkpoint de la tarea

        # Comprobar si la tarea esta completada del todo, si la columna existe es que está terminada
        if column in _benchmark.columns: 
            continue
        
        target_labels= []
        
        # Si existe un chekcpoint cargar el progreso en target_labels
        if os.path.exists(f"{chk_point}.csv"):
            target_labels= pd.read_csv(f"{chk_point}.csv")[column].to_list()

        start = len(target_labels)  # el siguiente índice a procesar
        prompts = _benchmark[task_type].to_list()
        n = len(prompts)

        ### EDIT:
        for batch_start in range(start, n, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, n)
            batch_prompts = prompts[batch_start:batch_end]
            
            # 1) Renderizado para el modelo
            rendered_batch = [
                render_prompt_for_model(p, pretrained_model_name, tokenizer)
                for p in batch_prompts
            ]
        
            # 2) TRUNCADO SEGURO DEL PROMPT PERO EN BATCH
            tokenized = tokenizer(
                rendered_batch,
                truncation=True,
                max_length=max_input_tokens,
                padding=False,            # o "longest" si quieres padding
                return_tensors=None,      # devolvemos listas de ids
            )
        
            # tokenized["input_ids"] es una lista de listas de ids
            truncated_batch = tokenizer.batch_decode(
                tokenized["input_ids"],
                skip_special_tokens=False,
            )
        
            # 3) Llamada al pipeline en batch
            outputs = pipe(truncated_batch, **limited_gen_cfg)
            
            # 4) Procesar cada salida del batch
            for out in outputs:
                prompt_response = out[0]["generated_text"]
                if prompt_response:
                    prompt_response = extract_response(prompt_response)
                target_labels.append(prompt_response)
        
            # 5) Guardar checkpoint por batch
            pd.DataFrame({column: target_labels}).to_csv(f"{chk_point}.csv", index=False)
            torch.cuda.empty_cache()
            print(
                f"Checkpoint saved ({len(target_labels)} instancias procesadas, hasta índice {batch_end-1})",
                flush=True,
            )
        #####

        
        # for prompt in prompts[start:]:
        #     prompt= render_prompt_for_model(prompt, pretrained_model_name, tokenizer)

        #     # --- TRUNCADO SEGURO DEL PROMPT ---
        #     encoded = tokenizer.encode(
        #         prompt,
        #         truncation=True,
        #         max_length=max_input_tokens,
        #     )

        #     truncated_prompt = tokenizer.decode(
        #         encoded,
        #         skip_special_tokens=False,
        #     )
        #     # ---------------------------

        #     prompt_response= pipe(truncated_prompt, **limited_gen_cfg)[0]["generated_text"]
            
        #     # prompt_response= prompt_response.split("")[-1]
        #     if prompt_response:
        #         prompt_response= extract_response(prompt_response)
        #     target_labels.append(prompt_response)

        #     if len(target_labels)%BATCH_SIZE == 0:
        #         pd.DataFrame({column: target_labels}).to_csv(f"{chk_point}.csv", index=False)
        #         torch.cuda.empty_cache()
        #         print(f"Checkpoint saved", flush=True)

        _benchmark[column]= target_labels

        pd.DataFrame({column: target_labels}).to_csv(f"{chk_point}.csv", index=False)
        print(f"Last checkpoint saved", flush=True)
        _benchmark[column]= target_labels
        
        _benchmark.to_csv(f"{OUT_CSV}.csv", index=False)
        print(f"Task {task_type} finished", flush=True)
        
        if os.path.exists(f"{chk_point}.csv"):
            os.remove(f"{chk_point}.csv")
        print(f"Checkpoints removed", flush=True)

    print(f"Model {pretrained_model_name} finished", flush=True)

if __name__ == "__main__":
    # Argument parser
    parser = argparse.ArgumentParser(description="Temporal Reasoning Experiment")
    parser.add_argument("--benchmark_file", type=str, required=True, help="Path to the benchmark CSV file")
    parser.add_argument("--benchmark_name", type=str, required=True, help="Name of the benchmark")
    parser.add_argument("--pretrained_model_name", type=str, required=True, help="Name of the pretrained model to use")
    parser.add_argument("--experiments", type=str, nargs='+', default=["0s_question"], help="List of experiments to evaluate (columns of the csv)")
    parser.add_argument("--batch_size", type=int, required=False, default=256, help="Pipeline and checkpoint batch size.")
    
    args = parser.parse_args()

    # Assign arguments to variables
    benchmark_file = args.benchmark_file
    benchmark_name = args.benchmark_name
    pretrained_model_name = args.pretrained_model_name
    task_types = args.experiments
    batch_size= args.batch_size
    
    # Load benchmark dataset
    benchmark= pd.read_csv(benchmark_file)
    temporal_reasoning_experiment(benchmark, benchmark_name, pretrained_model_name, task_types, batch_size)

