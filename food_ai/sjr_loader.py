#!/usr/bin/env python3
"""
SJR translated note
translated note Morvan translated note scimagojr_2024.csv
"""

import csv
import json
from pathlib import Path
from typing import Dict, Optional


class SJRJournalData:
    """SJR translated note"""
    
    def __init__(self, csv_path: str = None):
        """
        translated note SJR translated note
        
        Args:
            csv_path: SJR CSV translated note,translated note Morvan translated note
        """
        if csv_path is None:
            # translated note Morvan translated note
            csv_path = "/root/.openclaw/media/inbound/scimagojr_2024---4f3ddd10-a223-4f97-b697-5b553c96d46f.csv"
        
        self.csv_path = Path(csv_path)
        self.journals: Dict[str, dict] = {}
        self._load_data()
    
    def _load_data(self):
        """translated note CSV translated note"""
        print(f"📥 translated note SJR translated note: {self.csv_path}")
        
        if not self.csv_path.exists():
            print(f"    translated note: {self.csv_path}")
            return
        
        count = 0
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            for row in reader:
                title = row.get('Title', '').strip().strip('"')
                issn = row.get('Issn', '').strip()
                
                # translated note SJR translated note(translated note:CSV translated note)
                sjr_str = row.get('SJR', '0').replace(',', '.')
                try:
                    sjr = float(sjr_str)
                except ValueError:
                    sjr = 0.0
                
                # translated note H-index
                h_index_str = row.get('H index', '0')
                try:
                    h_index = int(h_index_str)
                except ValueError:
                    h_index = 0
                
                # translated note quartile
                quartile = row.get('SJR Best Quartile', 'Q4')
                
                if title:
                    self.journals[title.lower()] = {
                        'title': title,
                        'issn': issn,
                        'sjr': sjr,
                        'h_index': h_index,
                        'quartile': quartile,
                        'publisher': row.get('Publisher', ''),
                        'country': row.get('Country', '')
                    }
                    count += 1
        
        print(f"   ✓ translated note: {count} translated note")
    
    def get_journal(self, journal_name: str) -> Optional[dict]:
        """
        translated note
        
        Args:
            journal_name: translated note(translated note)
        
        Returns:
            translated note,translated note None
        """
        if not journal_name:
            return None
        
        journal_lower = journal_name.lower().strip()
        
        # 1. translated note
        if journal_lower in self.journals:
            return self.journals[journal_lower]
        
        # 2. translated note(translated note)
        for title, data in self.journals.items():
            if journal_lower in title or title in journal_lower:
                return data
        
        # 3. translated note(translated note)
        keywords = journal_lower.replace('journal', '').replace('of', '').replace('and', '').replace('the', '').strip()
        if keywords:
            for title, data in self.journals.items():
                if keywords in title:
                    return data
        
        return None
    
    def get_score(self, journal_name: str) -> tuple:
        """
        translated note (0-10)
        
        Returns:
            (score, tier, sjr_value)
        """
        journal = self.get_journal(journal_name)
        
        if not journal:
            return 3.0, "unranked", 0.0  # translated note
        
        sjr = journal.get('sjr', 0)
        
        # SJR translated note 0-10 translated note
        # SJR translated note 0-150,translated note 0-10
        if sjr >= 10.0:
            score = 10.0
            tier = "top"
        elif sjr >= 5.0:
            score = 9.0
            tier = "excellent"
        elif sjr >= 3.0:
            score = 8.0
            tier = "high"
        elif sjr >= 2.0:
            score = 7.0
            tier = "good"
        elif sjr >= 1.0:
            score = 6.0
            tier = "medium"
        elif sjr >= 0.5:
            score = 5.0
            tier = "fair"
        elif sjr > 0:
            score = 4.0
            tier = "low"
        else:
            score = 3.0
            tier = "unranked"
        
        return score, tier, sjr
    
    def get_stats(self) -> dict:
        """translated note"""
        if not self.journals:
            return {}
        
        sjrs = [j['sjr'] for j in self.journals.values() if j['sjr'] > 0]
        
        return {
            'total_journals': len(self.journals),
            'sjr_max': max(sjrs) if sjrs else 0,
            'sjr_min': min(sjrs) if sjrs else 0,
            'sjr_avg': sum(sjrs) / len(sjrs) if sjrs else 0,
            'top_journals': len([j for j in self.journals.values() if j['sjr'] >= 10]),
            'high_journals': len([j for j in self.journals.values() if 5 <= j['sjr'] < 10])
        }
    
    def save_to_json(self, output_path: str):
        """translated note JSON translated note"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.journals, f, indent=2, ensure_ascii=False)
        print(f"💾 translated note: {output_path}")


if __name__ == "__main__":
    # translated note
    sjr_data = SJRJournalData()
    
    # translated note
    stats = sjr_data.get_stats()
    print(f"\n SJR translated note:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")
    
    # translated note
    test_journals = [
        "Nature Medicine",
        "Journal of Dairy Science",
        "Nutrients",
        "Unknown Journal"
    ]
    
    print(f"\n translated note:")
    for journal in test_journals:
        score, tier, sjr = sjr_data.get_score(journal)
        info = sjr_data.get_journal(journal)
        if info:
            print(f"   {journal}: {score}translated note ({tier}, SJR={sjr:.3f})")
        else:
            print(f"   {journal}: {score}translated note ({tier}, translated note)")
