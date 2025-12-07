import re
from collections import Counter


def extract_keywords(text):
    if not text:
        return set()
    # Simple stop words list (can be expanded)
    stop_words = {'and', 'the', 'is', 'in', 'at', 'of', 'for', 'to', 'a', 'an', 'with', 'on', 'by'}
    
    # Tokenize, lower case, remove punctuation
    words = re.findall(r'\w+', text.lower())
    
    # Filter stop words and short words
    keywords = {w for w in words if w not in stop_words and len(w) > 2}
    return keywords

def calculate_similarity(student_skills, visit_text):
    if not student_skills or not visit_text:
        return 0.0
        
    student_keywords = extract_keywords(student_skills)
    visit_keywords = extract_keywords(visit_text)
    
    if not visit_keywords:
        return 0.0
        
    # intersection
    common = student_keywords.intersection(visit_keywords)
    
    # simple Jaccard index concept or just overlap ratio
    score = len(common) / len(visit_keywords)
    return round(score * 100, 1) # Return percentage

def get_recommendations(student, all_visits):
    """
    Returns a list of (visit, match_score) sorted by score desc.
    """
    recommendations = []
    
    for visit in all_visits:
        # Combine title, description, company for matching
        visit_content = f"{visit.title} {visit.description} {visit.visit_type} {visit.company_name}"
        score = calculate_similarity(student.skills, visit_content)
        
        # Only recommend if there is some relevance (e.g. > 0%) or give a boost for "fresh" visits
        # For demo purposes, we return everything sorted, but maybe highlight high scores
        recommendations.append({
            'visit': visit,
            'score': score
        })
        
    # Sort by score descending
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    return recommendations
