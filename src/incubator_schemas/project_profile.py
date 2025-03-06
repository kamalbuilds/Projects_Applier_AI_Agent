from dataclasses import dataclass
from typing import List, Dict, Optional
import yaml
from pydantic import BaseModel, EmailStr, HttpUrl, Field
from src.logging import logger

class TeamMember(BaseModel):
    full_name: str
    role: str
    email: Optional[EmailStr] = None
    linkedin: Optional[HttpUrl] = None
    github: Optional[HttpUrl] = None
    bio: str
    skills: List[str]
    years_experience: int
    education: List[Dict[str, str]]

class ProjectBasicInfo(BaseModel):
    project_name: str
    tagline: str  # One-line description
    website: Optional[HttpUrl] = None
    github_repo: Optional[HttpUrl] = None
    founding_date: Optional[str] = None
    development_stage: str  # e.g., "Idea", "Prototype", "MVP", "Growth"
    sector: str  # e.g., "Fintech", "Healthtech", "AI/ML"
    industry: List[str]

class ProjectDetails(BaseModel):
    problem_statement: str
    solution_description: str
    unique_value_proposition: str
    target_audience: str
    market_size: Optional[str] = None
    business_model: str
    revenue_streams: List[str]
    competitors: List[Dict[str, str]]  # {"name": "Company X", "differentiator": "How we differ"}
    traction: Optional[str] = None  # Current metrics, users, revenue
    roadmap: Dict[str, str]  # {"Q1 2023": "Feature X launch", "Q2 2023": "Expand to market Y"}

class TechnicalDetails(BaseModel):
    tech_stack: List[str]
    intellectual_property: Optional[str] = None
    scalability_approach: Optional[str] = None
    current_challenges: List[str]
    future_technological_needs: List[str]

class Funding(BaseModel):
    funding_to_date: Optional[str] = None
    funding_sources: Optional[List[str]] = None
    current_runway: Optional[str] = None
    funding_needed: Optional[str] = None
    use_of_funds: Optional[Dict[str, str]] = None  # {"Development": "40%", "Marketing": "30%"}

class IncubatorPreferences(BaseModel):
    resources_needed: List[str]  # e.g., "Mentorship", "Office Space", "Legal Support"
    program_length_preference: str  # e.g., "3 months", "6 months"
    equity_willingness: Optional[str] = None  # e.g., "Up to 5%", "Negotiable"
    relocation_willingness: bool
    remote_participation: bool
    specific_mentors_desired: Optional[List[str]] = None
    
class ProjectProfile(BaseModel):
    team: List[TeamMember]
    basic_info: ProjectBasicInfo
    details: ProjectDetails
    technical: TechnicalDetails
    funding: Funding
    incubator_preferences: IncubatorPreferences
    
    @classmethod
    def from_yaml(cls, yaml_str: str):
        logger.debug("Initializing ProjectProfile with provided YAML string")
        try:
            data = yaml.safe_load(yaml_str)
            logger.debug(f"YAML data successfully parsed")
            return cls(
                team=[TeamMember(**member) for member in data.get('team', [])],
                basic_info=ProjectBasicInfo(**data.get('basic_info', {})),
                details=ProjectDetails(**data.get('details', {})),
                technical=TechnicalDetails(**data.get('technical', {})),
                funding=Funding(**data.get('funding', {})),
                incubator_preferences=IncubatorPreferences(**data.get('incubator_preferences', {}))
            )
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            raise ValueError("Error parsing YAML file.") from e
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            raise RuntimeError(f"An unexpected error occurred: {e}") from e
    
    def to_dict(self):
        """Convert the project profile to a dictionary."""
        return {
            "team": [member.dict() for member in self.team],
            "basic_info": self.basic_info.dict(),
            "details": self.details.dict(),
            "technical": self.technical.dict(),
            "funding": self.funding.dict(),
            "incubator_preferences": self.incubator_preferences.dict()
        }
    
    def __str__(self):
        """Return a string representation of the project profile."""
        return (
            f"Project: {self.basic_info.project_name}\n"
            f"Tagline: {self.basic_info.tagline}\n"
            f"Stage: {self.basic_info.development_stage}\n"
            f"Team Size: {len(self.team)} members\n"
            f"Sectors: {self.basic_info.sector}, {', '.join(self.basic_info.industry)}"
        ) 