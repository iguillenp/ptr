from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd


class SPARQL:
    def __init__(self, **kwargs) -> None:
        """Initialize the SPARQL endpoint for querying.

        Args:
            endpoint (None): Could be a known endpoint (wikidata). Or custom url.
        """

        self.kwonw_endpoints= {
            "wikidata": "https://query.wikidata.org/bigdata/namespace/wdq/sparql"
        }

        if "endpoint" in kwargs:
            if kwargs["endpoint"].startswith("http"):
                self.sparql = SPARQLWrapper(kwargs["endpoint"])
            else:
                self.sparql = SPARQLWrapper(self.kwonw_endpoints[kwargs["endpoint"]])
        else:
            self.sparql = SPARQLWrapper("")

        self.sparql.setReturnFormat(JSON)
        self.sparql.setMethod("POST") 
        self.sparql.addCustomHttpHeader("User-Agent", "PoliticalDiscourse/1.0 (ibai.guillen@upm.es)")

    def run_query_pandas(self, query):
        if self.sparql.endpoint == "": raise Exception("No endpoint configured. Please set endpoint.")
        self.sparql.setQuery(query)
        results = self.sparql.query().convert()

        sparql_dict_result= {}
        for label in results["head"]["vars"]:
            if len(results["results"]["bindings"]) >= 1:
                if label not in sparql_dict_result: sparql_dict_result[label]= []
                for result in results["results"]["bindings"]:
                    try:
                        sparql_dict_result[label].append(result[label]["value"])
                    except:
                        sparql_dict_result[label].append(None)
            # elif len(results["results"]["bindings"]) == 1:
            #     result= results["results"]["bindings"][0]
            #     sparql_dict_result[label]= result[label]["value"]
            else:
                sparql_dict_result[label]= None

        try:
            return pd.DataFrame(sparql_dict_result)
        except:
            return None
    
    def run_query_dict(self, query):
        if self.sparql.endpoint == "": raise Exception("No endpoint configured. Please set endpoint.")
        self.sparql.setQuery(query)
        results = self.sparql.query().convert()

        sparql_dict_result= {}
        for label in results["head"]["vars"]:
            if len(results["results"]["bindings"]) > 1:
                if label not in sparql_dict_result: sparql_dict_result[label]= []
                for result in results["results"]["bindings"]:
                    sparql_dict_result[label].append(result[label]["value"])
            elif len(results["results"]["bindings"]) == 1:
                result= results["results"]["bindings"][0]
                sparql_dict_result[label]= result[label]["value"]
            else:
                sparql_dict_result[label]= None

        return sparql_dict_result
    
    def run_query_raw(self, query):
        if self.sparql.endpoint == "": raise Exception("No endpoint configured. Please set endpoint.")
        self.sparql.setQuery(query)
        results = self.sparql.query().convert()

        return results

    def set_endpoint(self, endpoint):
        self.sparql.endpoint= endpoint

    def set_endpoint_wikidata(self):
        self.sparql.endpoint= self.kwonw_endpoints["wikidata"]
