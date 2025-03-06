import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
import yaml
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from src.logging import logger
from src.incubator_schemas.project_profile import ProjectProfile

@dataclass
class IncubatorQuestion:
    question_id: str
    question_text: str
    max_chars: Optional[int] = None
    expected_content: Optional[str] = None  # Hint about what kind of content is expected
    answered: bool = False
    answer: str = ""

@dataclass
class IncubatorApplication:
    program_name: str
    application_url: str
    deadline: str
    questions: List[IncubatorQuestion] = field(default_factory=list)
    project_profile: Optional[ProjectProfile] = None
    
    def __post_init__(self):
        self.id = f"{self.program_name.replace(' ', '_').lower()}_{self.deadline.replace('-', '')}"
    
    def add_question(self, question_id: str, question_text: str, max_chars: Optional[int] = None, 
                    expected_content: Optional[str] = None):
        """Add a question to the application."""
        question = IncubatorQuestion(
            question_id=question_id,
            question_text=question_text,
            max_chars=max_chars,
            expected_content=expected_content
        )
        self.questions.append(question)
        return question
    
    def load_project_profile(self, profile_path: str):
        """Load project profile from a YAML file."""
        try:
            with open(profile_path, 'r') as file:
                yaml_str = file.read()
                self.project_profile = ProjectProfile.from_yaml(yaml_str)
                logger.info(f"Loaded project profile for {self.project_profile.basic_info.project_name}")
        except Exception as e:
            logger.error(f"Failed to load project profile: {e}")
            raise
    
    def answer_question(self, question_id: str, answer: str):
        """Manually answer a specific question."""
        for question in self.questions:
            if question.question_id == question_id:
                question.answer = answer
                question.answered = True
                return True
        return False
    
    def generate_answers(self, api_key: str, model_name: str = "gpt-4", temperature: float = 0.7):
        """Generate answers for all unanswered questions using AI."""
        if not self.project_profile:
            raise ValueError("Project profile must be loaded before generating answers")
        
        # Choose the appropriate model based on the model_name
        if model_name.startswith("gpt"):
            llm = ChatOpenAI(openai_api_key=api_key, model_name=model_name, temperature=temperature)
        elif model_name.startswith("claude"):
            llm = ChatAnthropic(anthropic_api_key=api_key, model_name=model_name, temperature=temperature)
        elif model_name.startswith("gemini"):
            llm = ChatGoogleGenerativeAI(google_api_key=api_key, model_name=model_name, temperature=temperature)
        else:
            raise ValueError(f"Unsupported model: {model_name}")
        
        # Convert project profile to a string representation for the prompt
        project_data = yaml.dump(self.project_profile.to_dict())
        
        for question in self.questions:
            if not question.answered:
                prompt_template = PromptTemplate(
                    input_variables=["question", "project_info", "max_chars", "expected_content"],
                    template="""
                    You are an AI assistant helping a startup answer questions for an incubator application.
                    
                    Here is information about the startup project:
                    {project_info}
                    
                    Please answer the following question for the incubator application:
                    "{question}"
                    
                    {expected_content_text}
                    {max_chars_text}
                    
                    Your answer should be well-structured, specific, and persuasive. Use concrete examples and 
                    details from the provided project information. Format appropriately.
                    """
                )
                
                # Add conditional text for max_chars and expected_content
                max_chars_text = f"Your answer must be under {question.max_chars} characters." if question.max_chars else ""
                expected_content_text = f"The answer should focus on: {question.expected_content}" if question.expected_content else ""
                
                chain = LLMChain(llm=llm, prompt=prompt_template)
                
                try:
                    response = chain.run(
                        question=question.question_text,
                        project_info=project_data,
                        max_chars_text=max_chars_text,
                        expected_content_text=expected_content_text
                    )
                    
                    # Trim response if it exceeds max_chars
                    if question.max_chars and len(response) > question.max_chars:
                        response = response[:question.max_chars]
                    
                    question.answer = response.strip()
                    question.answered = True
                    logger.info(f"Generated answer for question: {question.question_id}")
                except Exception as e:
                    logger.error(f"Failed to generate answer for question {question.question_id}: {e}")
        
        return [q for q in self.questions if q.answered]
    
    def export_answers(self, output_path: str):
        """Export all answered questions to a JSON file."""
        answers = {
            "program_name": self.program_name,
            "application_url": self.application_url,
            "deadline": self.deadline,
            "answers": [
                {
                    "question_id": q.question_id,
                    "question": q.question_text,
                    "answer": q.answer
                }
                for q in self.questions if q.answered
            ]
        }
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(answers, f, indent=2)
            logger.info(f"Exported answers to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to export answers: {e}")
            raise

    def load_from_json(self, json_path: str):
        """Load application questions from a JSON file."""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            self.program_name = data.get("program_name", self.program_name)
            self.application_url = data.get("application_url", self.application_url)
            self.deadline = data.get("deadline", self.deadline)
            
            # Load questions
            questions = data.get("questions", [])
            for q in questions:
                self.add_question(
                    question_id=q.get("question_id", f"q{len(self.questions)+1}"),
                    question_text=q.get("question_text", ""),
                    max_chars=q.get("max_chars"),
                    expected_content=q.get("expected_content")
                )
            
            # Load answers if available
            answers = data.get("answers", [])
            for a in answers:
                self.answer_question(a.get("question_id"), a.get("answer", ""))
                
            logger.info(f"Loaded application with {len(self.questions)} questions from {json_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load application from JSON: {e}")
            return False 