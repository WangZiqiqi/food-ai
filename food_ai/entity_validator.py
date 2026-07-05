"""
Food-AI translated note
translated note,translated note,translated note
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """translated note"""
    is_valid: bool
    normalized_name: str
    errors: List[str]
    warnings: List[str]
    entity_type: str


class StrainValidator:
    """translated note - translated note"""

    # translated note (translated note + translated note)
    # translated note [\w\-]+ translated note (translated note BB-12)
    VALID_PATTERNS = [
        # Lactobacillus rhamnosus GG
        r'^[A-Z][a-z]+\s+[a-z]+\s+[\w\-]+$',
        # L. rhamnosus GG (translated note)
        r'^[A-Z]\.\s*[a-z]+\s+[\w\-]+$',
        # Bifidobacterium animalis subsp. lactis BB-12
        r'^[A-Z][a-z]+\s+[a-z]+\s+subsp\.\s+[a-z]+\s+[\w\-]+$',
        # L. rhamnosus subsp. lactis GG
        r'^[A-Z]\.\s*[a-z]+\s+subsp\.\s+[a-z]+\s+[\w\-]+$',
        # Lactobacillus rhamnosus subsp. rhamnosus ATCC 53103
        r'^[A-Z][a-z]+\s+[a-z]+\s+subsp\.\s+[a-z]+\s+[A-Z]+[\s\-]*\d+$',
    ]

    # translated note - translated note
    BLACKLIST = {
        'not reported', 'not specified', 'na', 'n/a', 'unknown', 'unspecified',
        'phage therapy', 'bacteriophage therapy', 'probiotic', 'probiotics',
        'beneficial microbes', 'beneficial bacteria', 'commensal bacteria',
        'gut microbiota', 'gut microbiome', 'intestinal microbiota',
        'fermented food', 'fermented foods', 'fermented product',
        'fortified yogurt', 'fortified milk', 'fortified drink',
        'mixed probiotics', 'probiotic mixture', 'probiotic blend',
        'commercial probiotic', 'probiotic supplement', 'probiotic product',
        'yogurt drink', 'yogurt beverage', 'fermented dairy',
        'kefir grains', 'scoby', 'kombucha culture',
    }

    # translated note
    CORRECTIONS = {
        'lactobacillus': 'Lactobacillus',
        'bifidobacterium': 'Bifidobacterium',
        'streptococcus': 'Streptococcus',
        'lactococcus': 'Lactococcus',
        'leuconostoc': 'Leuconostoc',
        'pediococcus': 'Pediococcus',
        'enterococcus': 'Enterococcus',
        'bacillus': 'Bacillus',
        'saccharomyces': 'Saccharomyces',
    }

    def validate(self, name: str) -> ValidationResult:
        """
        translated note

        translated note ValidationResult:
            - is_valid: translated note
            - normalized_name: translated note
            - errors: translated note
            - warnings: translated note
        """
        if not name or not isinstance(name, str):
            return ValidationResult(
                is_valid=False,
                normalized_name='',
                errors=['Empty or invalid name'],
                warnings=[],
                entity_type='strain'
            )

        original_name = name.strip()
        errors = []
        warnings = []

        # 1. translated note
        name_lower = original_name.lower()
        if name_lower in self.BLACKLIST:
            return ValidationResult(
                is_valid=False,
                normalized_name='',
                errors=[f'Blacklisted term: {original_name}'],
                warnings=[],
                entity_type='strain'
            )

        # 2. translated note
        for black_term in self.BLACKLIST:
            if black_term in name_lower:
                return ValidationResult(
                    is_valid=False,
                    normalized_name='',
                    errors=[f'Contains blacklisted term: {black_term}'],
                    warnings=[],
                    entity_type='strain'
                )

        # 3. translated note
        normalized = self._normalize(original_name)

        # 4. translated note
        if not self._check_format(normalized):
            errors.append(f'Invalid strain format: {normalized}')
            errors.append('Expected format: Genus species strain_id (e.g., Lactobacillus rhamnosus GG)')

        # 5. translated note
        if len(normalized) < 5:
            errors.append('Name too short')
        if len(normalized) > 100:
            warnings.append('Name suspiciously long')

        # 6. translated note(translated note)
        if self._contains_chinese(normalized):
            errors.append('Strain name should not contain Chinese characters')

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            normalized_name=normalized if is_valid else '',
            errors=errors,
            warnings=warnings,
            entity_type='strain'
        )

    def _normalize(self, name: str) -> str:
        """translated note"""
        # translated note
        normalized = ' '.join(name.split())

        # translated note
        for wrong, correct in self.CORRECTIONS.items():
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            normalized = pattern.sub(correct, normalized)

        # translated note
        words = normalized.split()
        if words:
            words[0] = words[0].capitalize()
            if len(words) > 1:
                words[1] = words[1].lower()
        normalized = ' '.join(words)

        return normalized

    def _check_format(self, name: str) -> bool:
        """translated note"""
        for pattern in self.VALID_PATTERNS:
            if re.match(pattern, name):
                return True
        return False

    def _contains_chinese(self, text: str) -> bool:
        """translated note"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def extract_strain_info(self, name: str) -> Dict:
        """translated note"""
        result = {
            'genus': '',
            'species': '',
            'subspecies': '',
            'strain_id': '',
            'full_name': name
        }

        parts = name.split()
        if len(parts) >= 2:
            # translated note: L. rhamnosus -> Lactobacillus rhamnosus
            if parts[0].endswith('.') and len(parts[0]) == 2:
                result['genus'] = parts[0][0]  # translated note
            else:
                result['genus'] = parts[0]

            # translated note subsp.
            if 'subsp.' in parts:
                subsp_idx = parts.index('subsp.')
                if subsp_idx > 0:
                    result['species'] = parts[subsp_idx - 1]
                    if subsp_idx + 1 < len(parts):
                        result['subspecies'] = parts[subsp_idx + 1]
                        if subsp_idx + 2 < len(parts):
                            result['strain_id'] = ' '.join(parts[subsp_idx + 2:])
            else:
                result['species'] = parts[1]
                if len(parts) > 2:
                    result['strain_id'] = ' '.join(parts[2:])

        return result


class FoodNameNormalizer:
    """translated note - translated note"""

    # translated note (translated note)
    SYNONYMS = {
        'yoghurt': 'yogurt',
        'yoghurts': 'yogurt',
        'yogurts': 'yogurt',
        'probiotic yogurt': 'probiotic_yogurt',
        'fermented dairy': 'fermented_dairy',
        'dairy products': 'dairy',
        'milk product': 'dairy',
        'kephir': 'kefir',
        'kafir': 'kefir',
    }

    INVALID_EXACT_TERMS = {
        'placebo',
        'intervention',
        'comparison',
        'control',
        'baseline',
        'biological_factor',
        'biological factor',
        'male',
        'female',
        'male sex',
        'female sex',
    }

    INVALID_PATTERNS = [
        r'^male(?:_| )',
        r'^female(?:_| )',
        r'^control(?:_| )',
        r'^placebo(?:_| )?',
        r'^comparison$',
        r'^intervention$',
        r'^conditioning_',
        r'^week\d*$',
        r'^day[_\s-]?\d+',
        r'^month\d*$',
        r'^follow[_\s-]?up',
    ]

    def normalize(self, name: str) -> str:
        """translated note"""
        if not name:
            return ''

        original = name.strip().lower()

        # translated note (translated note)
        for synonym, standard in self.SYNONYMS.items():
            if original == synonym or original.startswith(synonym + ' '):
                original = original.replace(synonym, standard, 1)

        # Keep intervention qualifiers out of the canonical food node when they
        # are better represented as dose/formulation attributes on evidence.
        original = re.sub(r'\s*\(?3\.25%\s*fat\)?', '', original)
        original = re.sub(r'\s*\((dy|dcy|py)\)\s*$', '', original)
        original = original.replace('vitamin d + calcium-fortified yogurt drink',
                                    'vitamin d calcium fortified yogurt drink')
        original = original.replace('vitamin d- or vitamin d + calcium-fortified yogurt drink',
                                    'vitamin d fortified yogurt drink')
        if 'heat-killed lactobacillus paracasei k71' in original:
            original = 'heat-killed lactobacillus paracasei k71 supplement'
        if original in {'lab diet', 'lab diet group'}:
            original = 'heat-killed lactobacillus paracasei k71 supplement'
        if 'greek yogurt' in original and (
            'exercise' in original or 'training' in original or '+' in original
        ):
            original = 'greek yogurt'
        if 'lactobacillus rhamnosus gr-1' in original and (
            'yogurt' in original or 'yoghurt' in original
        ):
            original = 'probiotic yogurt'
        if original.startswith('probiotic_yogurt containing') or original.startswith('probiotic yogurt containing'):
            original = 'probiotic yogurt'
        if 'bacillus coagulans' in original and 'inulin' in original:
            original = 'synbiotic supplement'
        if 'with greek yogurt' in original or 'greek yogurt consumption' in original:
            original = 'greek yogurt'
        if (
            original.startswith('combination of bifidobacterium')
            or original.startswith('multi-strain probiotic')
            or original.startswith('multi-strain combination')
        ):
            original = 'multi strain probiotic formulation'
        if original.startswith('yogurt containing'):
            original = 'probiotic yogurt'
        if original.startswith('yeast containing saccharomyces cerevisiae'):
            original = 'saccharomyces cerevisiae yeast'
        original = original.replace('probiotic/synbiotic', 'probiotic synbiotic')

        # translated note
        normalized = self._clean_format(original)

        return normalized

    def validate(self, name: str) -> ValidationResult:
        """translated note food translated note."""
        if not name or not isinstance(name, str):
            return ValidationResult(
                is_valid=False,
                normalized_name='',
                errors=['Empty or invalid food name'],
                warnings=[],
                entity_type='food'
            )

        original = name.strip()
        normalized = self.normalize(original)
        normalized_text = normalized.replace('_', ' ')
        errors = []
        warnings = []

        if normalized in self.INVALID_EXACT_TERMS or normalized_text in self.INVALID_EXACT_TERMS:
            errors.append(f'Blacklisted food term: {original}')

        for pattern in self.INVALID_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE) or re.search(pattern, normalized_text, re.IGNORECASE):
                errors.append(f'Suspicious non-food pattern matched: {pattern}')
                break

        if len(normalized) <= 2:
            errors.append('Food name too short')

        if normalized.count('_') >= 6:
            warnings.append('Food name is unusually specific')

        return ValidationResult(
            is_valid=not errors,
            normalized_name=normalized if not errors else '',
            errors=errors,
            warnings=warnings,
            entity_type='food'
        )

    def _clean_format(self, name: str) -> str:
        """translated note"""
        # translated note
        name = ' '.join(name.split())

        # translated note
        name = name.replace(' ', '_')

        # translated note
        name = re.sub(r'_+', '_', name)

        # translated note
        name = name.strip('_')

        return name


class EntityValidator:
    """translated note"""

    def __init__(self):
        self.strain_validator = StrainValidator()
        self.food_normalizer = FoodNameNormalizer()

    def validate_food_name(self, name: str) -> ValidationResult:
        """translated note food translated note."""
        return self.food_normalizer.validate(name)

    def validate_strains(self, strains: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        translated note

        translated note: (valid_strains, invalid_strains)
        """
        valid = []
        invalid = []

        for strain in strains:
            name = strain.get('name', '')
            result = self.strain_validator.validate(name)

            if result.is_valid:
                # translated note
                strain['name'] = result.normalized_name
                # translated note
                strain_info = self.strain_validator.extract_strain_info(result.normalized_name)
                strain.update(strain_info)
                valid.append(strain)
            else:
                invalid.append({
                    'original': name,
                    'errors': result.errors,
                    'warnings': result.warnings
                })

        return valid, invalid

    def normalize_foods(self, foods: List[Dict]) -> List[Dict]:
        """translated note"""
        normalized = []

        for food in foods:
            name = food.get('name', '')
            validation = self.food_normalizer.validate(name)
            normalized_name = validation.normalized_name

            if normalized_name:
                food['name'] = normalized_name
                food['original_name'] = name  # translated note
                if validation.warnings:
                    food['validation_warnings'] = validation.warnings
                normalized.append(food)

        return normalized

    def filter_orphan_entities(self, entities: Dict, claims: List[Dict]) -> Dict:
        """
        translated note(translated noteclaimtranslated note)

        translated noteclaimstranslated note
        """
        # translated note
        referenced_names = set()
        for claim in claims:
            sub_name = claim.get('subject_name', '')
            obj_name = claim.get('object_name', '')
            sub_type = claim.get('subject_type', '')
            obj_type = claim.get('object_type', '')

            if sub_name and sub_type:
                referenced_names.add((sub_type, sub_name.lower()))
            if obj_name and obj_type:
                referenced_names.add((obj_type, obj_name.lower()))

        # translated note
        filtered = {
            'foods': [],
            'strains': [],
            'populations': [],
            'outcomes': []
        }

        type_mapping = {
            'foods': 'food_product',
            'strains': 'strain',
            'populations': 'population',
            'outcomes': 'outcome'
        }

        for entity_type, entity_list in entities.items():
            claim_type = type_mapping.get(entity_type, entity_type)
            for entity in entity_list:
                name = entity.get('name', '').lower()
                if (claim_type, name) in referenced_names:
                    filtered[entity_type].append(entity)

        return filtered

    def validate_extraction_result(self, result: Dict) -> Dict:
        """
        translated note

        translated note
        """
        entities = result.get('entities', {})
        claims = result.get('claims', [])

        validation_report = {
            'original_counts': {
                'foods': len(entities.get('foods', [])),
                'strains': len(entities.get('strains', [])),
                'populations': len(entities.get('populations', [])),
                'outcomes': len(entities.get('outcomes', [])),
                'claims': len(claims)
            },
            'validation': {}
        }

        # 1. translated note
        valid_strains, invalid_strains = self.validate_strains(
            entities.get('strains', [])
        )
        entities['strains'] = valid_strains
        validation_report['validation']['strains'] = {
            'valid': len(valid_strains),
            'invalid': len(invalid_strains),
            'invalid_details': invalid_strains[:5]  # translated note5translated note
        }

        # 2. translated note
        entities['foods'] = self.normalize_foods(entities.get('foods', []))

        # 3. translated note
        entities = self.filter_orphan_entities(entities, claims)

        validation_report['filtered_counts'] = {
            'foods': len(entities.get('foods', [])),
            'strains': len(entities.get('strains', [])),
            'populations': len(entities.get('populations', [])),
            'outcomes': len(entities.get('outcomes', [])),
        }

        result['entities'] = entities
        result['validation_report'] = validation_report

        return result


# translated note
def validate_strain_name(name: str) -> bool:
    """translated note"""
    validator = StrainValidator()
    result = validator.validate(name)
    return result.is_valid


def normalize_food_name(name: str) -> str:
    """translated note"""
    normalizer = FoodNameNormalizer()
    return normalizer.normalize(name)


if __name__ == '__main__':
    # translated note
    validator = StrainValidator()

    test_cases = [
        'Lactobacillus rhamnosus GG',  # translated note
        'L. rhamnosus GG',  # translated note(translated note)
        'Bifidobacterium animalis subsp. lactis BB-12',  # translated note
        'not reported',  # translated note(translated note)
        'phage therapy',  # translated note(translated note)
        'translated note',  # translated note(translated note)
        'Lactobacillus',  # translated note(translated note)
        'some random text',  # translated note(translated note)
    ]

    print("=== Strain Validator Test ===")
    for name in test_cases:
        result = validator.validate(name)
        status = "" if result.is_valid else ""
        print(f"{status} '{name}'")
        if not result.is_valid:
            print(f"   Errors: {result.errors}")
        else:
            info = validator.extract_strain_info(result.normalized_name)
            print(f"   Normalized: {result.normalized_name}")
            print(f"   Info: {info}")
        print()

    # translated note
    normalizer = FoodNameNormalizer()
    food_tests = [
        'translated note',
        'yoghurt',
        'fermented dairy',
        'probiotic yogurt',
    ]

    print("=== Food Normalizer Test ===")
    for name in food_tests:
        normalized = normalizer.normalize(name)
        print(f"'{name}' -> '{normalized}'")
