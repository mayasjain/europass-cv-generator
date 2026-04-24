"""
Data models for the CV pipeline.
Each section of the Europass CV is represented as a Pydantic model.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class PersonalInfo(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    linkedin: str = ""
    website: str = ""
    nationality: str = ""
    date_of_birth: str = ""


class WorkExperience(BaseModel):
    job_title: str = ""
    employer: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""          # use "Present" if current
    description: list[str] = []  # bullet points


class Project(BaseModel):
    title: str = ""
    role: str = ""
    location: str = ""          # or URL / organisation
    start_date: str = ""
    end_date: str = ""
    description: list[str] = []  # bullet points


class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""


class Extracurricular(BaseModel):
    organisation: str = ""
    role: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    description: list[str] = []  # bullet points


class Language(BaseModel):
    name: str = ""
    level: str = ""             # e.g. "Native", "B2", "Fluent"


class Skill(BaseModel):
    category: str = ""          # e.g. "Programming", "Tools"
    items: list[str] = []


class CVData(BaseModel):
    personal: PersonalInfo = PersonalInfo()
    work_experience: list[WorkExperience] = []
    projects: list[Project] = []
    education: list[Education] = []
    extracurriculars: list[Extracurricular] = []
    languages: list[Language] = []
    skills: list[Skill] = []
    interests: list[str] = []
