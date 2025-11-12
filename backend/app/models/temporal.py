"""Temporal extraction models for extracting dates, deadlines, and time references from meeting transcripts."""
import re
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Tuple, Optional, Union
from dataclasses import dataclass
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


@dataclass
class TemporalEntity:
    """Represents a temporal entity found in text."""
    text: str
    parsed_date: Optional[datetime]
    temporal_type: str  # 'date', 'deadline', 'duration', 'frequency'
    start: int
    end: int
    confidence: float = 1.0
    context: str = ""


class RuleBasedTemporal:
    """Rule-based temporal extraction for meeting contexts."""
    
    def __init__(self):
        self.today = datetime.now().date()
        
        # Date patterns
        self.date_patterns = {
            'explicit_date': [
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
                r'\b\d{4}-\d{2}-\d{2}\b'  # ISO format
            ],
            'relative_date': [
                r'\btomorrow\b',
                r'\btoday\b',
                r'\byesterday\b',
                r'\bnext\s+(?:week|month|quarter|year)\b',
                r'\blast\s+(?:week|month|quarter|year)\b',
                r'\bthis\s+(?:week|month|quarter|year)\b',
                r'\bin\s+\d+\s+(?:days?|weeks?|months?|years?)\b',
                r'\bwithin\s+\d+\s+(?:days?|weeks?|months?)\b'
            ],
            'day_of_week': [
                r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
                r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b'
            ],
            'time_expressions': [
                r'\b\d{1,2}:\d{2}(?:\s*(?:AM|PM|am|pm))?\b',
                r'\b(?:morning|afternoon|evening|noon)\b',
                r'\bby\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b'
            ]
        }
        
        # Deadline patterns
        self.deadline_patterns = [
            r'\bdue\s+(?:by\s+)?([^,.]+)\b',
            r'\bdeadline\s+(?:is\s+)?([^,.]+)\b',
            r'\bby\s+(?:the\s+)?end\s+of\s+([^,.]+)\b',
            r'\bmust\s+be\s+(?:completed|done|finished)\s+by\s+([^,.]+)\b',
            r'\bEOD\b|\bCOB\b',  # End of Day, Close of Business
            r'\bASAP\b',  # As Soon As Possible
            r'\bby\s+([A-Z][a-z]+day)\b',  # by Monday, Tuesday, etc.
            r'\bbefore\s+([^,.]+)\b'
        ]
        
        # Duration patterns
        self.duration_patterns = [
            r'\b\d+\s*(?:minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?)\b',
            r'\b(?:a|an|one)\s+(?:minute|hour|day|week|month|year)\b',
            r'\b(?:several|few|couple\s+of)\s+(?:minutes|hours|days|weeks|months)\b'
        ]
        
        # Frequency patterns
        self.frequency_patterns = [
            r'\b(?:daily|weekly|monthly|quarterly|annually|yearly)\b',
            r'\bevery\s+(?:day|week|month|quarter|year)\b',
            r'\bevery\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
            r'\bonce\s+(?:a|per)\s+(?:day|week|month|quarter|year)\b',
            r'\btwice\s+(?:a|per)\s+(?:day|week|month|year)\b'
        ]
        
        # Holiday patterns (for business context)
        self.holiday_patterns = [
            r'\b(?:Christmas|Thanksgiving|New\s+Year|Easter|Memorial\s+Day|Labor\s+Day)\b',
            r'\b(?:holiday|vacation)\b'
        ]
    
    def extract_temporal_entities(self, text: str, reference_date: Optional[datetime] = None) -> List[TemporalEntity]:
        """Extract temporal entities from text."""
        if reference_date is None:
            reference_date = datetime.now()
        
        entities = []
        
        # Extract explicit dates
        entities.extend(self._extract_explicit_dates(text))
        
        # Extract relative dates
        entities.extend(self._extract_relative_dates(text, reference_date))
        
        # Extract deadlines
        entities.extend(self._extract_deadlines(text, reference_date))
        
        # Extract durations
        entities.extend(self._extract_durations(text))
        
        # Extract frequencies
        entities.extend(self._extract_frequencies(text))
        
        # Remove duplicates and overlaps
        entities = self._remove_overlaps(entities)
        
        return entities
    
    def _extract_explicit_dates(self, text: str) -> List[TemporalEntity]:
        """Extract explicit date mentions."""
        entities = []
        
        for category, patterns in self.date_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    date_text = match.group().strip()
                    parsed_date = self._parse_date(date_text)
                    
                    entity = TemporalEntity(
                        text=date_text,
                        parsed_date=parsed_date,
                        temporal_type='date',
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9 if parsed_date else 0.5,
                        context=category
                    )
                    entities.append(entity)
        
        return entities
    
    def _extract_relative_dates(self, text: str, reference_date: datetime) -> List[TemporalEntity]:
        """Extract relative date expressions."""
        entities = []
        
        relative_mappings = {
            'today': timedelta(days=0),
            'tomorrow': timedelta(days=1),
            'yesterday': timedelta(days=-1),
            'next week': timedelta(weeks=1),
            'last week': timedelta(weeks=-1),
            'this week': timedelta(days=0),  # Approximate
            'next month': relativedelta(months=1),
            'last month': relativedelta(months=-1),
            'this month': timedelta(days=0),
            'next quarter': relativedelta(months=3),
            'next year': relativedelta(years=1)
        }
        
        for pattern in self.date_patterns['relative_date']:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                relative_text = match.group().strip().lower()
                parsed_date = None
                
                # Direct mappings
                for key, delta in relative_mappings.items():
                    if key in relative_text:
                        if isinstance(delta, relativedelta):
                            parsed_date = reference_date + delta
                        else:
                            parsed_date = reference_date + delta
                        break
                
                # "In X days/weeks/months" patterns
                if not parsed_date:
                    in_match = re.match(r'in (\d+) (days?|weeks?|months?|years?)', relative_text)
                    if in_match:
                        number = int(in_match.group(1))
                        unit = in_match.group(2)
                        
                        if 'day' in unit:
                            parsed_date = reference_date + timedelta(days=number)
                        elif 'week' in unit:
                            parsed_date = reference_date + timedelta(weeks=number)
                        elif 'month' in unit:
                            parsed_date = reference_date + relativedelta(months=number)
                        elif 'year' in unit:
                            parsed_date = reference_date + relativedelta(years=number)
                
                entity = TemporalEntity(
                    text=match.group().strip(),
                    parsed_date=parsed_date,
                    temporal_type='relative_date',
                    start=match.start(),
                    end=match.end(),
                    confidence=0.8 if parsed_date else 0.6,
                    context='relative'
                )
                entities.append(entity)
        
        return entities
    
    def _extract_deadlines(self, text: str, reference_date: datetime) -> List[TemporalEntity]:
        """Extract deadline expressions."""
        entities = []
        
        for pattern in self.deadline_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                deadline_text = match.group().strip()
                parsed_date = None
                
                # Handle special cases
                if deadline_text.upper() in ['EOD', 'COB']:
                    # End of day - set to 5 PM today
                    parsed_date = reference_date.replace(hour=17, minute=0, second=0, microsecond=0)
                elif deadline_text.upper() == 'ASAP':
                    # As soon as possible - set to now + 1 hour
                    parsed_date = reference_date + timedelta(hours=1)
                else:
                    # Try to extract date from captured group
                    if match.groups():
                        date_part = match.group(1).strip()
                        parsed_date = self._parse_date(date_part, reference_date)
                
                entity = TemporalEntity(
                    text=deadline_text,
                    parsed_date=parsed_date,
                    temporal_type='deadline',
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9 if parsed_date else 0.7,
                    context='deadline'
                )
                entities.append(entity)
        
        return entities
    
    def _extract_durations(self, text: str) -> List[TemporalEntity]:
        """Extract duration expressions."""
        entities = []
        
        for pattern in self.duration_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                duration_text = match.group().strip()
                
                entity = TemporalEntity(
                    text=duration_text,
                    parsed_date=None,  # Durations don't have specific dates
                    temporal_type='duration',
                    start=match.start(),
                    end=match.end(),
                    confidence=0.8,
                    context='duration'
                )
                entities.append(entity)
        
        return entities
    
    def _extract_frequencies(self, text: str) -> List[TemporalEntity]:
        """Extract frequency expressions."""
        entities = []
        
        for pattern in self.frequency_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                frequency_text = match.group().strip()
                
                entity = TemporalEntity(
                    text=frequency_text,
                    parsed_date=None,  # Frequencies don't have specific dates
                    temporal_type='frequency',
                    start=match.start(),
                    end=match.end(),
                    confidence=0.8,
                    context='frequency'
                )
                entities.append(entity)
        
        return entities
    
    def _parse_date(self, date_text: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
        """Parse a date string into a datetime object."""
        try:
            # Use dateutil parser which handles many formats
            parsed = date_parser.parse(date_text, fuzzy=True, default=reference_date)
            return parsed
        except (ValueError, TypeError) as e:
            logger.debug(f"Could not parse date '{date_text}': {e}")
            return None
    
    def _remove_overlaps(self, entities: List[TemporalEntity]) -> List[TemporalEntity]:
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
    
    def extract_action_deadlines(self, text: str, reference_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Extract action items with their associated deadlines."""
        if reference_date is None:
            reference_date = datetime.now()
        
        action_deadlines = []
        
        # Pattern to match action items with deadlines
        action_deadline_patterns = [
            r'([^.]+?)\s+(?:by|due|before)\s+([^.]+)',
            r'([^.]+?)\s+deadline\s+(?:is\s+)?([^.]+)',
            r'([^.]+?)\s+must\s+be\s+(?:completed|done|finished)\s+by\s+([^.]+)'
        ]
        
        for pattern in action_deadline_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                action_text = match.group(1).strip()
                deadline_text = match.group(2).strip()
                
                parsed_deadline = self._parse_date(deadline_text, reference_date)
                
                action_deadline = {
                    'action': action_text,
                    'deadline_text': deadline_text,
                    'deadline_date': parsed_deadline,
                    'confidence': 0.8 if parsed_deadline else 0.6,
                    'text_span': (match.start(), match.end())
                }
                action_deadlines.append(action_deadline)
        
        return action_deadlines
    
    def get_next_business_day(self, reference_date: datetime, days: int = 1) -> datetime:
        """Get the next business day (excluding weekends)."""
        current = reference_date
        while days > 0:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Monday = 0, Sunday = 6
                days -= 1
        return current
    
    def is_business_day(self, check_date: datetime) -> bool:
        """Check if a date is a business day (Monday-Friday)."""
        return check_date.weekday() < 5


class DucklingTemporal:
    """Duckling-based temporal extraction (if available)."""
    
    def __init__(self, duckling_url: str = "http://localhost:8000"):
        self.duckling_url = duckling_url
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Duckling service is available."""
        try:
            import requests
            response = requests.get(f"{self.duckling_url}/parse", timeout=1)
            return response.status_code == 200
        except Exception:
            logger.warning("Duckling service not available, falling back to rule-based temporal extraction")
            return False
    
    def extract_temporal_entities(self, text: str) -> List[TemporalEntity]:
        """Extract temporal entities using Duckling."""
        if not self.available:
            raise ValueError("Duckling service not available")
        
        try:
            import requests
            
            data = {
                "locale": "en_US",
                "text": text,
                "dims": ["time", "duration", "cycle"]
            }
            
            response = requests.post(f"{self.duckling_url}/parse", data=data)
            response.raise_for_status()
            
            results = response.json()
            entities = []
            
            for result in results:
                entity = TemporalEntity(
                    text=result["body"],
                    parsed_date=self._parse_duckling_time(result.get("value")),
                    temporal_type=result["dim"],
                    start=result["start"],
                    end=result["end"],
                    confidence=0.95,
                    context="duckling"
                )
                entities.append(entity)
            
            return entities
        
        except Exception as e:
            logger.error(f"Duckling extraction failed: {e}")
            raise
    
    def _parse_duckling_time(self, value: Dict[str, Any]) -> Optional[datetime]:
        """Parse Duckling time value."""
        if not value:
            return None
        
        if value.get("type") == "value":
            return datetime.fromisoformat(value["value"].replace("Z", "+00:00"))
        
        return None


def get_temporal_extractor(provider: str = "rule_based", **kwargs) -> Union[RuleBasedTemporal, DucklingTemporal]:
    """Factory function to get temporal extractor based on provider."""
    if provider == "duckling":
        duckling_url = kwargs.get("duckling_url", "http://localhost:8000")
        return DucklingTemporal(duckling_url)
    elif provider == "rule_based":
        return RuleBasedTemporal()
    else:
        raise ValueError(f"Unknown temporal extraction provider: {provider}")