"""Entity recognition models for extracting structured information from meeting transcripts."""
import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents a named entity found in text."""
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0


class RuleBasedNER:
    """Rule-based Named Entity Recognition for meeting contexts."""
    
    def __init__(self):
        self.patterns = {
            'PERSON': [
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
                r'\b[A-Z]\. [A-Z][a-z]+\b',      # J. Doe
                r'\b[A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+\b'  # Complex names
            ],
            'DATE': [
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
                r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)day\b',
                r'\btomorrow\b|\btoday\b|\byesterday\b',
                r'\bnext\s+(?:week|month|quarter)\b',
                r'\bby\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday)\b'
            ],
            'TIME': [
                r'\b\d{1,2}:\d{2}(?:\s*(?:AM|PM|am|pm))?\b',
                r'\b(?:morning|afternoon|evening|noon)\b',
                r'\bby\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b'
            ],
            'DEADLINE': [
                r'\bdue\s+(?:by\s+)?\w+\b',
                r'\bdeadline\s+(?:is\s+)?\w+\b',
                r'\bby\s+(?:the\s+)?end\s+of\s+\w+\b',
                r'\bEOD\b|\bCOB\b'  # End of Day, Close of Business
            ],
            'MONEY': [
                r'\$[\d,]+(?:\.\d{2})?\s*(?:million|billion|thousand|k|M|B)?\b',
                r'\b\d+(?:\.\d+)?\s*(?:million|billion|thousand)\s*dollars?\b',
                r'\bbudget\s+of\s+\$?[\d,]+\b'
            ],
            'PROJECT': [
                r'\bProject\s+[A-Z][a-zA-Z0-9\s]+\b',
                r'\b[A-Z][a-zA-Z0-9]+\s+(?:project|initiative|campaign)\b'
            ],
            'COMPANY': [
                r'\b[A-Z][a-zA-Z0-9]+\s+(?:Inc|Corp|LLC|Ltd|Co)\b',
                r'\b(?:Google|Microsoft|Apple|Amazon|Facebook|Meta|Netflix|Tesla|IBM|Intel)\b'
            ]
        }
        
        # Common meeting role indicators
        self.role_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s+(?:our\s+)?(?:CEO|CTO|VP|director|manager|lead)\b',
            r'\b(?:CEO|CTO|VP|director|manager|lead)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        ]
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text using rule-based patterns."""
        entities = []
        
        for label, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity = Entity(
                        text=match.group().strip(),
                        label=label,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.8
                    )
                    entities.append(entity)
        
        # Extract people with roles
        entities.extend(self._extract_people_with_roles(text))
        
        # Remove duplicates and overlaps
        entities = self._remove_overlaps(entities)
        
        return entities
    
    def _extract_people_with_roles(self, text: str) -> List[Entity]:
        """Extract people mentioned with their roles."""
        entities = []
        
        for pattern in self.role_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(1).strip()
                entity = Entity(
                    text=name,
                    label='PERSON_WITH_ROLE',
                    start=match.start(1),
                    end=match.end(1),
                    confidence=0.9
                )
                entities.append(entity)
        
        return entities
    
    def _remove_overlaps(self, entities: List[Entity]) -> List[Entity]:
        """Remove overlapping entities, keeping the one with highest confidence."""
        entities.sort(key=lambda x: x.start)
        filtered = []
        
        for entity in entities:
            overlap = False
            for existing in filtered:
                if (entity.start < existing.end and entity.end > existing.start):
                    if entity.confidence > existing.confidence:
                        filtered.remove(existing)
                    else:
                        overlap = True
                        break
            
            if not overlap:
                filtered.append(entity)
        
        return filtered
    
    def extract_action_owners(self, text: str) -> List[str]:
        """Extract potential action item owners from text."""
        owners = []
        
        # Direct assignment patterns
        assignment_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+will\s+',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+to\s+(?:handle|complete|do|work on)',
            r'assign(?:ed)?\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:is\s+)?responsible\s+for',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+should\s+',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+can\s+(?:you\s+)?(?:please\s+)?'
        ]
        
        for pattern in assignment_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                owner = match.group(1).strip()
                if owner and owner not in owners:
                    owners.append(owner)
        
        return owners


class SpacyNER:
    """spaCy-based Named Entity Recognition."""
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self.nlp = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize spaCy model."""
        try:
            import spacy
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Loaded spaCy model: {self.model_name}")
        except ImportError:
            logger.warning("spaCy not available, falling back to rule-based NER")
            raise
        except OSError:
            logger.warning(f"spaCy model {self.model_name} not found, falling back to rule-based NER")
            raise
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities using spaCy."""
        if not self.nlp:
            raise ValueError("spaCy model not initialized")
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entity = Entity(
                text=ent.text,
                label=ent.label_,
                start=ent.start_char,
                end=ent.end_char,
                confidence=0.9
            )
            entities.append(entity)
        
        return entities
    
    def extract_action_owners(self, text: str) -> List[str]:
        """Extract potential action owners using spaCy's dependency parsing."""
        if not self.nlp:
            return []
        
        doc = self.nlp(text)
        owners = []
        
        # Look for PERSON entities that are subjects of action verbs
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # Check if this person is the subject of an action verb
                for token in ent:
                    if token.dep_ == "nsubj" and token.head.pos_ == "VERB":
                        if ent.text not in owners:
                            owners.append(ent.text)
                        break
        
        return owners


def get_entity_recognizer(provider: str = "rule_based", **kwargs) -> Any:
    """Factory function to get entity recognizer based on provider."""
    if provider == "spacy":
        model_name = kwargs.get("model_name", "en_core_web_sm")
        return SpacyNER(model_name)
    elif provider == "rule_based":
        return RuleBasedNER()
    else:
        raise ValueError(f"Unknown entity recognition provider: {provider}")