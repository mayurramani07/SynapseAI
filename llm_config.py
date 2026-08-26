import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def get_provider_llms():
    """Build prioritized list of available LLM providers and models for automatic fallback."""
    providers = []

    if GROQ_API_KEY:
        groq_models = [
            ("Groq (gpt-oss-20b)", "openai/gpt-oss-20b"),
            ("Groq (gpt-oss-120b)", "openai/gpt-oss-120b"),
            ("Groq (compound-mini)", "groq/compound-mini"),
            ("Groq (qwen-27b)", "qwen/qwen3.6-27b")
        ]
        for name, model_id in groq_models:
            try:
                providers.append({
                    "name": name,
                    "llm": ChatGroq(
                        model=model_id,
                        temperature=0.2,
                        api_key=GROQ_API_KEY,
                        max_retries=0
                    )
                })
            except Exception:
                pass

    google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if google_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            providers.append({
                "name": "Gemini (gemini-1.5-flash)",
                "llm": ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    temperature=0.2,
                    google_api_key=google_key
                )
            })
        except Exception:
            pass

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            from langchain_openai import ChatOpenAI
            providers.append({
                "name": "OpenRouter (llama-3.1-8b)",
                "llm": ChatOpenAI(
                    model="meta-llama/llama-3.1-8b-instruct:free",
                    openai_api_key=openrouter_key,
                    openai_api_base="https://openrouter.ai/api/v1",
                    temperature=0.2
                )
            })
        except Exception:
            pass

    return providers


provider_pool = get_provider_llms()
llm = provider_pool[0]["llm"] if provider_pool else None


def execute_prompt_with_fallback(prompt, input_dict, json_mode=False):
    """Executes a prompt against LLM providers in order. Fails over immediately on rate-limit/TPD/404 errors.
    
    Args:
        json_mode: If True, requests JSON-only output from providers that support it (Groq, OpenAI).
                   This reduces parsing failures by preventing conversational prefixes/suffixes.
    """
    last_error = None
    providers = get_provider_llms()

    for provider in providers:
        try:
            provider_llm = provider["llm"]

            # Apply JSON mode if the provider supports it (Groq / OpenAI compatible)
            if json_mode and hasattr(provider_llm, "bind"):
                try:
                    provider_llm = provider_llm.bind(
                        response_format={"type": "json_object"}
                    )
                except Exception:
                    pass  # Provider doesn't support response_format, fall back to default

            chain = prompt | provider_llm | StrOutputParser()
            result = chain.invoke(input_dict)
            return result
        except Exception as error:
            last_error = error
            error_text = str(error).lower()
            if any(p in error_text for p in ["rate limit", "tpm", "tpd", "429", "404", "model_not_found", "quota", "503", "500"]):
                continue
            raise error

    if last_error:
        raise last_error
    raise RuntimeError("No LLM provider available.")

