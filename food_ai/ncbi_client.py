"""
NCBI Taxonomy translated note - translated note
"""

import requests
import time
from typing import Dict, Optional, List, Any
import xml.etree.ElementTree as ET


class NCBITaxonomyClient:
    """NCBI Taxonomy API translated note"""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, api_key: Optional[str] = None, delay: float = 0.34):
        """
        translated note
        
        Args:
            api_key: NCBI API key (translated note,translated note)
            delay: translated note(translated note),translated noteAPI keytranslated note0.34translated note
        """
        self.api_key = api_key
        self.delay = delay if not api_key else 0.1
        self.last_request_time = 0
    
    def _rate_limit(self):
        """translated note"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()
    
    def search_taxonomy(self, term: str, retmax: int = 10) -> List[Dict]:
        """
        translated note NCBI Taxonomy
        
        Args:
            term: translated note
            retmax: translated note
            
        Returns:
            translated note
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}/esearch.fcgi"
        params = {
            "db": "taxonomy",
            "term": term,
            "retmode": "json",
            "retmax": retmax
        }
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            id_list = data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return []
            
            # translated note
            return self.fetch_taxonomy_details(id_list)
            
        except Exception as e:
            print(f"NCBI search error: {e}")
            return []
    
    def fetch_taxonomy_details(self, tax_ids: List[str]) -> List[Dict]:
        """
        translated note
        
        Args:
            tax_ids: Taxonomy ID translated note
            
        Returns:
            translated note
        """
        if not tax_ids:
            return []
        
        self._rate_limit()
        
        url = f"{self.BASE_URL}/esummary.fcgi"
        params = {
            "db": "taxonomy",
            "id": ",".join(tax_ids),
            "retmode": "json"
        }
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for tax_id in tax_ids:
                doc = data.get("result", {}).get(tax_id, {})
                if doc:
                    results.append(self._parse_taxonomy_doc(doc))
            
            return results
            
        except Exception as e:
            print(f"NCBI fetch error: {e}")
            return []
    
    def _parse_taxonomy_doc(self, doc: Dict) -> Dict:
        """translated note taxonomy translated note"""
        return {
            "tax_id": doc.get("taxid"),
            "scientific_name": doc.get("scientificname"),
            "common_name": doc.get("commonname"),
            "rank": doc.get("rank"),
            "division": doc.get("division"),
            "genetic_code": doc.get("gcode"),
            "mitochondrial_genetic_code": doc.get("mgcode"),
            "lineage": doc.get("lineage"),
        }
    
    def fetch_full_lineage(self, tax_id: str) -> Optional[Dict]:
        """
        translated note
        
        Args:
            tax_id: Taxonomy ID
            
        Returns:
            translated note genus, species translated note
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}/efetch.fcgi"
        params = {
            "db": "taxonomy",
            "id": tax_id,
            "retmode": "xml"
        }
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            result = {
                "tax_id": tax_id,
                "genus": None,
                "species": None,
                "strain": None,
                "lineage": []
            }
            
            # translated note
            for taxon in root.findall(".//Taxon"):
                rank = taxon.findtext("Rank", "")
                name = taxon.findtext("ScientificName", "")
                
                if rank == "genus":
                    result["genus"] = name
                elif rank == "species":
                    result["species"] = name
                elif rank == "strain":
                    result["strain"] = name
                
                if rank and name:
                    result["lineage"].append({"rank": rank, "name": name})
            
            return result
            
        except Exception as e:
            print(f"NCBI lineage fetch error: {e}")
            return None
    
    def enrich_strain_info(self, strain_name: str) -> Optional[Dict]:
        """
        translated note NCBI translated note
        
        Args:
            strain_name: translated note
            
        Returns:
            translated note,translated note None translated note
        """
        # translated note
        results = self.search_taxonomy(strain_name, retmax=5)
        
        if not results:
            return None
        
        # translated note
        best_match = results[0]
        tax_id = best_match.get("tax_id")
        
        # translated note
        lineage = self.fetch_full_lineage(tax_id)
        
        if lineage:
            return {
                "original_name": strain_name,
                "ncbi_tax_id": tax_id,
                "scientific_name": best_match.get("scientific_name"),
                "genus": lineage.get("genus"),
                "species": lineage.get("species"),
                "strain": lineage.get("strain"),
                "rank": best_match.get("rank"),
                "lineage": lineage.get("lineage", [])
            }
        
        return None


# translated note
class CachedNCBIClient(NCBITaxonomyClient):
    """translated note NCBI translated note"""
    
    def __init__(self, cache_path: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache: Dict[str, Any] = {}
        self.cache_path = cache_path
        
        # translated note
        if cache_path:
            self._load_cache()
    
    def _load_cache(self):
        """translated note"""
        import json
        import os
        
        if self.cache_path and os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r') as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"Cache load error: {e}")
                self.cache = {}
    
    def _save_cache(self):
        """translated note"""
        import json
        
        if self.cache_path:
            try:
                with open(self.cache_path, 'w') as f:
                    json.dump(self.cache, f, indent=2)
            except Exception as e:
                print(f"Cache save error: {e}")
    
    def enrich_strain_info(self, strain_name: str) -> Optional[Dict]:
        """translated note"""
        # translated note
        if strain_name in self.cache:
            return self.cache[strain_name]
        
        # translated note
        result = super().enrich_strain_info(strain_name)
        
        # translated note
        self.cache[strain_name] = result
        self._save_cache()
        
        return result


# translated note
def enrich_strain_from_ncbi(strain_name: str, api_key: Optional[str] = None) -> Optional[Dict]:
    """translated note:translated note NCBI translated note"""
    client = NCBITaxonomyClient(api_key=api_key)
    return client.enrich_strain_info(strain_name)
