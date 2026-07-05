"""
PMC translated note - translated note NCBI E-utilities API
"""

import requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
from dataclasses import dataclass
import time


@dataclass
class FullTextContent:
    """PMC translated note"""
    pmcid: str
    pmid: str
    title: str
    abstract: str
    body_text: str
    tables: list
    sections: Dict[str, str]  # translated note -> translated note
    
    def get_methods_section(self) -> str:
        """translated note Methods translated note"""
        for key, value in self.sections.items():
            if "method" in key.lower():
                return value
        return ""
    
    def get_results_section(self) -> str:
        """translated note Results translated note"""
        for key, value in self.sections.items():
            if "result" in key.lower():
                return value
        return ""


def fetch_pmc_fulltext(pmcid: str) -> Optional[FullTextContent]:
    """
    translated note NCBI E-utilities API translated note PMC translated note
    
    Args:
        pmcid: PMC ID (translated note PMC translated note)
        
    Returns:
        FullTextContent translated note None
    """
    # translated note pmcid
    pmcid_clean = pmcid.replace("PMC", "").strip()
    
    # translated note E-utilities efetch API
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pmc",
        "id": pmcid_clean,
        "rettype": "xml",
    }
    
    try:
        print(f"    translated note PMC API: PMC{pmcid_clean}...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # translated note
        if "<ERROR>" in response.text or "<error>" in response.text:
            print(f"    Warning: API translated note,translated note OA translated note...")
            return fetch_pmc_oa(pmcid_clean)
        
        return parse_pmc_xml(response.text, pmcid_clean)
        
    except requests.exceptions.RequestException as e:
        print(f"    Warning: API translated note: {e},translated note OA translated note...")
        return fetch_pmc_oa(pmcid_clean)
    except Exception as e:
        print(f"    ✗ translated note: {e}")
        return None


def fetch_pmc_oa(pmcid: str) -> Optional[FullTextContent]:
    """
    translated note PMC Open Access translated note
    
    OA translated note URL: https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi
    """
    url = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
    params = {
        "id": f"PMC{pmcid}",
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # translated note OA translated note
        root = ET.fromstring(response.text)
        
        # translated note
        for link in root.findall('.//link'):
            format_type = link.get('format', '')
            href = link.get('href', '')
            
            # translated note XML translated note
            if format_type == 'xml' and href:
                print(f"    translated note OA XML: {href[:60]}...")
                xml_response = requests.get(href, timeout=30)
                xml_response.raise_for_status()
                return parse_pmc_xml(xml_response.text, pmcid)
        
        # translated note XML,translated note
        for link in root.findall('.//link'):
            format_type = link.get('format', '')
            href = link.get('href', '')
            
            if format_type in ['pdf', 'txt'] and href:
                print(f"    translated note OA {format_type}: {href[:60]}...")
                # translated note PDF/TXT,translated note None,translated note
                print(f"    Warning: {format_type} translated note")
                return None
        
        print(f"    ✗ translated note OA translated note")
        return None
        
    except Exception as e:
        print(f"    ✗ OA translated note: {e}")
        return None


def parse_pmc_xml(xml_content: str, pmcid: str) -> Optional[FullTextContent]:
    """translated note PMC XML"""
    try:
        root = ET.fromstring(xml_content)
        
        # translated note
        ns = {}
        if '}' in root.tag:
            namespace = root.tag.split('}')[0].strip('{')
            ns = {'ns': namespace}
        
        # translated note
        pmid = ""
        for article_id in root.findall('.//article-id', ns):
            if article_id.get('pub-id-type') == 'pmid':
                pmid = article_id.text or ""
                break
        
        # translated note pmid,translated note
        if not pmid:
            for article_id in root.findall('.//article-id'):
                if article_id.get('pub-id-type') == 'pmid':
                    pmid = article_id.text or ""
                    break
        
        title = ""
        title_elem = root.find('.//article-title', ns) or root.find('.//article-title')
        if title_elem is not None:
            title = ''.join(title_elem.itertext())
        
        # translated note
        abstract = ""
        abstract_elem = root.find('.//abstract', ns) or root.find('.//abstract')
        if abstract_elem is not None:
            abstract = ''.join(abstract_elem.itertext())
        
        # translated note
        sections = {}
        body_text = ""
        
        # translated note
        for sec in root.findall('.//sec', ns) or root.findall('.//sec'):
            title_elem = sec.find('title', ns) or sec.find('title')
            if title_elem is not None:
                sec_title = ''.join(title_elem.itertext())
                sec_text = ''.join(sec.itertext())
                sections[sec_title] = sec_text
                body_text += sec_text + "\n\n"
        
        # translated note
        tables = []
        for table in root.findall('.//table-wrap', ns) or root.findall('.//table-wrap'):
            table_text = ''.join(table.itertext())
            tables.append(table_text)
        
        # translated note,translated note body
        if not body_text:
            body = root.find('.//body', ns) or root.find('.//body')
            if body is not None:
                body_text = ''.join(body.itertext())
        
        return FullTextContent(
            pmcid=pmcid,
            pmid=pmid,
            title=title,
            abstract=abstract,
            body_text=body_text,
            tables=tables,
            sections=sections
        )
        
    except ET.ParseError as e:
        print(f"    ✗ XML translated note: {e}")
        return None
    except Exception as e:
        print(f"    ✗ translated note: {e}")
        return None


def extract_dose_from_fulltext(fulltext: FullTextContent) -> Optional[Dict[str, Any]]:
    """
    translated note
    
    translated note:
        {
            "value": float,
            "unit": str,
            "frequency": str,
            "duration_days": int,
            "source_text": str
        }
    """
    import re
    
    methods = fulltext.get_methods_section()
    if not methods:
        methods = fulltext.body_text[:10000]  # translated note10000translated note
    
    # translated note
    dose_patterns = [
        # CFU translated note: 10^9 CFU/day, 1x10^9 CFU, 10^9 CFU
        (r'(\d+(?:\.\d+)?)\s*(?:\u00d7|x|\*)?\s*10\^?(\d+)\s*(?:CFU|cfu)(?:/day)?', 'CFU'),
        # translated note: 1,000,000,000 CFU
        (r'(\d{1,3}(?:,\d{3})+)\s*(?:CFU|cfu)', 'CFU'),
        # translated note + CFU
        (r'(\d{10,})\s*(?:CFU|cfu)', 'CFU'),
        # g/day translated note
        (r'(\d+(?:\.\d+)?)\s*(g|mg|mcg)\s*(?:per|/)\s*(day|d)', 'weight'),
        # translated note + translated note
        (r'(\d+(?:\.\d+)?)\s*(g|mg|ml|capsules?|tablets?)\s*(?:daily|per day|/day)?', 'weight'),
    ]
    
    for pattern, unit_type in dose_patterns:
        match = re.search(pattern, methods, re.IGNORECASE)
        if match:
            value_str = match.group(1).replace(',', '')
            
            # translated note
            if len(match.groups()) >= 2 and unit_type == 'CFU':
                try:
                    base = float(value_str)
                    exponent = int(match.group(2))
                    value = base * (10 ** exponent)
                    return {
                        "value": value,
                        "unit": "CFU/day",
                        "frequency": "daily",
                        "duration_days": None,
                        "source_text": match.group(0)
                    }
                except (ValueError, IndexError):
                    pass
            
            # translated note
            try:
                value = float(value_str)
                unit = match.group(2) if len(match.groups()) > 1 else unit_type
                return {
                    "value": value,
                    "unit": unit,
                    "frequency": "daily" if "day" in match.group(0).lower() else None,
                    "duration_days": None,
                    "source_text": match.group(0)
                }
            except ValueError:
                continue
    
    return None


def extract_duration_from_fulltext(fulltext: FullTextContent) -> Optional[int]:
    """translated note(translated note)"""
    import re
    
    methods = fulltext.get_methods_section()
    if not methods:
        methods = fulltext.body_text[:10000]
    
    # translated note
    duration_patterns = [
        # translated note
        r'(?:for|over|during)\s+(\d+)\s*(?:weeks?|wk)',
        r'(?:for|over|during)\s+(\d+)\s*(?:months?|mo)',
        r'(?:for|over|during)\s+(\d+)\s*(?:days?|d)',
        # intervention/treatment duration
        r'intervention\s+(?:period|duration)\s*:?\s*(\d+)\s*(?:week|month|day)',
        r'treatment\s+(?:period|duration)\s*:?\s*(\d+)\s*(?:week|month|day)',
        # study duration
        r'study\s+(?:period|duration)\s*:?\s*(\d+)\s*(?:week|month|day)',
        # translated note + translated note
        r'(\d+)\s*(?:weeks?|wk)',
        r'(\d+)\s*(?:months?|mo)',
        r'(\d+)\s*(?:days?|d)',
    ]
    
    for pattern in duration_patterns:
        match = re.search(pattern, methods, re.IGNORECASE)
        if match:
            try:
                value = int(match.group(1))
                text = match.group(0).lower()
                
                # translated note
                if 'week' in text:
                    return value * 7
                elif 'month' in text:
                    return value * 30
                elif 'day' in text:
                    return value
            except (ValueError, IndexError):
                continue
    
    return None


def extract_sample_size_from_fulltext(fulltext: FullTextContent) -> Optional[int]:
    """translated note"""
    import re
    
    methods = fulltext.get_methods_section()
    if not methods:
        methods = fulltext.body_text[:10000]
    
    # translated note(translated note)
    patterns = [
        # translated note
        r'a\s+total\s+of\s+(\d+)\s*(?:participants?|subjects?|patients?|women|men|individuals?)',
        r'(\d+)\s*(?:participants?|subjects?|patients?|women|men|individuals?)\s*(?:were\s+)?(?:enrolled|recruited|included|randomized)',
        # n = X translated note
        r'(?:total\s+)?n\s*[=:]\s*(\d+)',
        # translated note + translated note
        r'(\d+)\s*(?:healthy\s+)?(?:volunteers?|subjects?|participants?|patients?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, methods, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None
