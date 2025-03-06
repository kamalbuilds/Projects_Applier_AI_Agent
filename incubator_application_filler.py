#!/usr/bin/env python3
import os
import click
import yaml
import json
from dotenv import load_dotenv
from src.logging import logger
from src.incubator_application import IncubatorApplication

load_dotenv()

@click.group()
def cli():
    """CLI for automatically filling out incubator program applications."""
    pass

@cli.command()
@click.argument('application_template', type=click.Path(exists=True))
@click.argument('project_profile', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Path to save the filled application.')
@click.option('--api-key', help='API key for the LLM service. Default: uses OPENAI_API_KEY env variable.')
@click.option('--model', default='gpt-4', help='LLM model to use. Supports gpt-*, claude-*, and gemini-* models.')
@click.option('--temperature', default=0.7, help='Temperature parameter for the LLM, controls randomness.')
def fill(application_template, project_profile, output, api_key, model, temperature):
    """Fill an incubator application template with project information."""
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key and model.startswith("gpt"):
            logger.error("No API key provided. Please provide one with --api-key or set OPENAI_API_KEY.")
            return
        
        # Check for other API keys based on model
        if model.startswith("claude") and not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                logger.error("No API key provided. Please provide one with --api-key or set ANTHROPIC_API_KEY.")
                return
        
        if model.startswith("gemini") and not api_key:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                logger.error("No API key provided. Please provide one with --api-key or set GOOGLE_API_KEY.")
                return

    # Generate default output path if not provided
    if not output:
        base_dir = "incubator_applications"
        os.makedirs(base_dir, exist_ok=True)
        output = os.path.join(base_dir, f"filled_{os.path.basename(application_template)}")
    
    try:
        # Load application template
        logger.info(f"Loading application template from {application_template}")
        with open(application_template, 'r') as f:
            template_data = json.load(f)
        
        # Create application object
        application = IncubatorApplication(
            program_name=template_data.get("program_name", "Unknown Program"),
            application_url=template_data.get("application_url", ""),
            deadline=template_data.get("deadline", "Unknown")
        )
        
        # Add questions from template
        for q in template_data.get("questions", []):
            application.add_question(
                question_id=q.get("question_id", f"q{len(application.questions)+1}"),
                question_text=q.get("question_text", ""),
                max_chars=q.get("max_chars"),
                expected_content=q.get("expected_content")
            )
        
        # Load project profile
        logger.info(f"Loading project profile from {project_profile}")
        application.load_project_profile(project_profile)
        
        # Generate answers
        logger.info(f"Generating answers using {model} model...")
        application.generate_answers(api_key, model_name=model, temperature=temperature)
        
        # Export filled application
        application.export_answers(output)
        logger.info(f"Filled application saved to {output}")
        
        # Display summary
        click.echo(f"Successfully filled {len(application.questions)} questions for {application.program_name}")
        click.echo(f"Results saved to: {output}")
        
    except Exception as e:
        logger.error(f"Error filling application: {e}")
        click.echo(f"Error: {e}")

@cli.command()
@click.argument('incubator_name')
@click.option('--questions', '-q', type=int, default=10, help='Number of questions to generate.')
@click.option('--url', '-u', help='URL of the incubator program.')
@click.option('--deadline', '-d', help='Application deadline (YYYY-MM-DD).')
@click.option('--output', '-o', type=click.Path(), help='Path to save the template.')
def create_template(incubator_name, questions, url, deadline, output):
    """Create a new incubator application template."""
    template = {
        "program_name": incubator_name,
        "application_url": url or "",
        "deadline": deadline or "",
        "questions": []
    }
    
    # Add placeholder questions
    for i in range(1, questions + 1):
        template["questions"].append({
            "question_id": f"q{i}",
            "question_text": f"Question {i}: Replace with actual question text",
            "max_chars": 1000,
            "expected_content": "Replace with hints about expected content"
        })
    
    # Generate default output path if not provided
    if not output:
        base_dir = "incubator_applications"
        os.makedirs(base_dir, exist_ok=True)
        sanitized_name = incubator_name.lower().replace(" ", "_")
        output = os.path.join(base_dir, f"{sanitized_name}_template.json")
    
    # Save the template
    with open(output, 'w') as f:
        json.dump(template, f, indent=2)
    
    logger.info(f"Created template for {incubator_name} with {questions} questions")
    click.echo(f"Template created at: {output}")
    click.echo("Edit the template to add your actual application questions.")

@cli.command()
@click.argument('filled_application', type=click.Path(exists=True))
def view(filled_application):
    """View a filled application."""
    try:
        with open(filled_application, 'r') as f:
            data = json.load(f)
        
        click.echo(f"\n====== {data.get('program_name', 'Unknown Program')} ======")
        click.echo(f"URL: {data.get('application_url', 'N/A')}")
        click.echo(f"Deadline: {data.get('deadline', 'N/A')}\n")
        
        for i, answer in enumerate(data.get('answers', []), 1):
            click.echo(f"Q{i}: {answer.get('question', '')}")
            click.echo(f"{'-' * 40}")
            click.echo(f"{answer.get('answer', '')}\n")
            click.echo()
        
    except Exception as e:
        logger.error(f"Error viewing application: {e}")
        click.echo(f"Error: {e}")

if __name__ == '__main__':
    cli() 