DEFAULT_SAMPLES = [
    "Hey [name] — loved your post on founder systems, hit close to home. I'm building an AI placement tool for students and your delegation framework is exactly what I needed. When did you know it was time to start delegating?",
    "Hey — saw you're building in the ops space. I'm working on something similar and would love your take on early traction. 5-min call possible this week?"
]

def get_voice_context(samples=None):
    """Builds a context string for the LLM to study and replicate the sender's voice"""
    if not samples:
        samples = DEFAULT_SAMPLES
    
    # Filter out empty strings and take first 3 only
    valid_samples = [s for s in samples if s.strip()][:3]
    
    if not valid_samples:
        return ""
    
    context = (
        "Here are writing samples from the sender. Study and replicate "
        "their exact style — sentence length, punctuation, tone, question format:\n\n"
    )
    
    for i, text in enumerate(valid_samples, 1):
        context += f"Sample {i}:\n{text}\n\n"
        
    return context.strip()
