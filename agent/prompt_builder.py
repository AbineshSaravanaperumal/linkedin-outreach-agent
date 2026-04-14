import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from agent.voice_calibrator import get_voice_context

TONE_GUIDE = {
    "Casual": "Conversational and warm. First name only. Short punchy sentences. End with one easy low-friction question.",
    "Professional": "Formal and respectful. Full clear sentences. One value proposition. Single question at end.",
    "Bold": "Confident and direct. Lead with a result or bold statement. Zero filler. One sharp question."
}

def get_api_key():
    """Returns API Key from secrets or .env"""
    try:
        import streamlit as st
        return st.secrets.get("OPENAI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        import os
        from dotenv import load_dotenv
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        )
        load_dotenv(env_path)
        return os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")

def generate_message(profile, user_bio, context, tone="Casual", voice_samples=None):
    """Generate a personalised LinkedIn message using LangChain + Google Gemini."""
    api_key = get_api_key()
    if not api_key:
        return "ERROR: Add your Google API key to the .env file first."

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.8,
            google_api_key=api_key
        )

        system_template = (
            "You are an expert at writing personalised LinkedIn cold outreach messages.\n\n"
            "Rules you never break:\n"
            "- Never use generic openers like 'I hope this message finds you well'\n"
            "- Never start with 'Hi' or 'Hello'\n"
            "- Always reference something SPECIFIC about the person\n"
            "- Always end with exactly ONE low-friction question\n"
            "- Keep the message under 100 words\n"
            "- No subject line, no sign-off\n\n"
            "Tone: {tone_instruction}\n\n"
            "{voice_context}"
        )

        user_template = (
            "Write a LinkedIn outreach message for this person:\n\n"
            "Name: {name}\n"
            "Current Role: {current_role}\n"
            "Company: {company}\n"
            "Headline: {headline}\n"
            "Recent activity: \"{recent_post}\"\n\n"
            "About me (sender):\n{user_bio}\n\n"
            "Why I am reaching out:\n{context}\n\n"
            "Write the message now. Under 100 words. "
            "Start directly with their first name or a bold opener."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", user_template)
        ])

        chain = prompt | llm | StrOutputParser()

        result = chain.invoke({
            "tone_instruction": TONE_GUIDE.get(tone, TONE_GUIDE["Casual"]),
            "voice_context": get_voice_context(voice_samples),
            "name": profile.get("name", "there"),
            "current_role": profile.get("current_role", "Professional"),
            "company": profile.get("company", "their company"),
            "headline": profile.get("headline", ""),
            "recent_post": profile.get("recent_post", "their recent work"),
            "user_bio": user_bio,
            "context": context or "General networking"
        })

        return result.strip()

    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "exceeded" in err or "billing" in err or "429" in err:
            return (
                "⚠️ API quota reached — message generation is temporarily paused.\n\n"
                "All other features still work normally.\n\n"
                "Fix: Check your API limits at makersuite.google.com/app/plan_information."
            )
        return f"Generation error: {str(e)}"
