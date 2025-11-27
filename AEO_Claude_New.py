# -*- coding: utf-8 -*-
"""
Created on Thu Nov 27 05:56:29 2025

@author: zubin
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import textstat
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(
    page_title="AEO On-Page Auditor",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #4F46E5;
        margin-bottom: 1rem;
    }
    .score-card {
        padding: 2rem;
        border-radius: 1rem;
        text-align: center;
        margin: 1rem 0;
    }
    .score-high {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .score-medium {
        background-color: #FEF3C7;
        color: #92400E;
    }
    .score-low {
        background-color: #FEE2E2;
        color: #991B1B;
    }
    .metric-card {
        padding: 1rem;
        background-color: #F9FAFB;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .priority-high {
        border-left: 4px solid #DC2626;
        background-color: #FEF2F2;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
    .priority-medium {
        border-left: 4px solid #F59E0B;
        background-color: #FFFBEB;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
    .priority-low {
        border-left: 4px solid #3B82F6;
        background-color: #EFF6FF;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def fetch_page(url):
    """Fetch webpage content"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def analyze_schema(soup):
    """Analyze structured data/schema markup"""
    schema_scripts = soup.find_all('script', type='application/ld+json')
    
    faq_present = False
    howto_present = False
    article_present = False
    faq_count = 0
    howto_count = 0
    
    for script in schema_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    schema_type = item.get('@type', '').lower()
                    if 'faqpage' in schema_type:
                        faq_present = True
                        faq_count = len(item.get('mainEntity', []))
                    elif 'howto' in schema_type:
                        howto_present = True
                        howto_count = len(item.get('step', []))
                    elif 'article' in schema_type:
                        article_present = True
            else:
                schema_type = data.get('@type', '').lower()
                if 'faqpage' in schema_type:
                    faq_present = True
                    faq_count = len(data.get('mainEntity', []))
                elif 'howto' in schema_type:
                    howto_present = True
                    howto_count = len(data.get('step', []))
                elif 'article' in schema_type:
                    article_present = True
        except:
            continue
    
    return {
        'faq_present': faq_present,
        'faq_count': faq_count,
        'howto_present': howto_present,
        'howto_count': howto_count,
        'article_present': article_present
    }

def analyze_questions(soup):
    """Analyze question-based content"""
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    question_words = ['what', 'why', 'how', 'when', 'where', 'who', 'which', 'can', 'is', 'are', 'do', 'does']
    question_headings = []
    
    for heading in headings:
        text = heading.get_text().strip().lower()
        if any(text.startswith(qw) for qw in question_words) or text.endswith('?'):
            question_headings.append(heading.get_text().strip())
    
    return {
        'total_headings': len(headings),
        'question_headings': len(question_headings),
        'question_heading_examples': question_headings[:5]
    }

def analyze_snippet_optimization(soup):
    """Analyze featured snippet readiness"""
    paragraphs = soup.find_all('p')
    first_para_words = 0
    
    if paragraphs:
        first_para_text = paragraphs[0].get_text().strip()
        first_para_words = len(first_para_text.split())
    
    lists = len(soup.find_all(['ul', 'ol']))
    tables = len(soup.find_all('table'))
    
    short_paragraphs = 0
    for p in paragraphs:
        word_count = len(p.get_text().split())
        if 40 <= word_count <= 60:
            short_paragraphs += 1
    
    snippet_score = 0
    if first_para_words >= 40 and first_para_words <= 60:
        snippet_score += 30
    if lists > 0:
        snippet_score += 25
    if tables > 0:
        snippet_score += 20
    if short_paragraphs >= 3:
        snippet_score += 25
    
    return {
        'first_para_words': first_para_words,
        'lists': lists,
        'tables': tables,
        'short_paragraphs': short_paragraphs,
        'snippet_score': min(snippet_score, 100)
    }

def analyze_structure(soup):
    """Analyze content structure"""
    text = soup.get_text()
    
    has_tldr = bool(re.search(r'(tl;?dr|summary|key takeaways)', text, re.IGNORECASE))
    has_toc = bool(soup.find(['div', 'nav'], class_=re.compile('toc|table-of-contents', re.I)))
    
    paragraphs = soup.find_all('p')
    if paragraphs:
        total_words = sum(len(p.get_text().split()) for p in paragraphs)
        avg_para_length = total_words / len(paragraphs)
    else:
        avg_para_length = 0
    
    word_count = len(text.split())
    
    try:
        flesch_score = textstat.flesch_reading_ease(text)
    except:
        flesch_score = 0
    
    return {
        'has_tldr': has_tldr,
        'has_toc': has_toc,
        'avg_para_length': round(avg_para_length, 1),
        'word_count': word_count,
        'flesch_reading_ease': round(flesch_score, 1)
    }

def analyze_entities(soup):
    """Basic entity extraction"""
    text = soup.get_text()
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    entities = list(set(words))
    entities_found = len(entities)
    
    return {
        'entities_found': entities_found,
        'entity_examples': entities[:10]
    }

def analyze_eeat(soup, url):
    """Analyze E-E-A-T signals"""
    author_meta = soup.find('meta', attrs={'name': re.compile('author', re.I)})
    has_author_meta = bool(author_meta)
    
    date_meta = soup.find('meta', attrs={'property': re.compile('published', re.I)})
    has_date = bool(date_meta)
    
    has_author_bio = bool(soup.find(['div', 'section'], class_=re.compile('author|bio', re.I)))
    
    links = soup.find_all('a', href=True)
    has_about_link = any('about' in link['href'].lower() for link in links)
    has_contact_link = any('contact' in link['href'].lower() for link in links)
    
    has_sources = bool(soup.find(['div', 'section'], class_=re.compile('reference|source|citation', re.I)))
    
    return {
        'has_author_meta': has_author_meta,
        'has_date': has_date,
        'has_author_bio': has_author_bio,
        'has_about_link': has_about_link,
        'has_contact_link': has_contact_link,
        'has_sources': has_sources
    }

def calculate_score_breakdown(data):
    """Calculate detailed score breakdown by component"""
    breakdown = {}
    
    schema_score = 0
    if data['schema']['faq_present']:
        schema_score += 10
    if data['schema']['howto_present']:
        schema_score += 10
    if data['schema']['article_present']:
        schema_score += 5
    breakdown['schema'] = {'score': schema_score, 'max': 25}
    
    question_score = min(data['questions']['question_headings'] * 4, 20)
    breakdown['questions'] = {'score': question_score, 'max': 20}
    
    snippet_score = data['snippet']['snippet_score'] * 0.2
    breakdown['snippet'] = {'score': round(snippet_score, 1), 'max': 20}
    
    structure_score = 0
    if data['structure']['has_tldr']:
        structure_score += 5
    if data['structure']['has_toc']:
        structure_score += 5
    if data['structure']['flesch_reading_ease'] >= 60:
        structure_score += 5
    breakdown['structure'] = {'score': structure_score, 'max': 15}
    
    eeat_score = sum([
        data['eeat']['has_author_meta'],
        data['eeat']['has_date'],
        data['eeat']['has_author_bio'],
        data['eeat']['has_sources']
    ]) * 2.5
    breakdown['eeat'] = {'score': eeat_score, 'max': 10}
    
    entity_score = 0
    if data['entities']['entities_found'] > 10:
        entity_score = 10
    elif data['entities']['entities_found'] > 5:
        entity_score = 5
    breakdown['entities'] = {'score': entity_score, 'max': 10}
    
    total_score = sum(item['score'] for item in breakdown.values())
    
    return {
        'breakdown': breakdown,
        'total': min(round(total_score), 100)
    }

def calculate_engine_scores(data):
    """Calculate scores for different AI engines"""
    base_breakdown = calculate_score_breakdown(data)
    
    engines = {
        'ChatGPT': {
            'weights': {
                'schema': 1.2,
                'questions': 1.1,
                'snippet': 1.0,
                'structure': 1.3,
                'eeat': 0.9,
                'entities': 1.0
            },
            'focus': 'Prioritizes conversational structure and clear formatting'
        },
        'Claude': {
            'weights': {
                'schema': 1.0,
                'questions': 1.2,
                'snippet': 1.0,
                'structure': 1.4,
                'eeat': 1.3,
                'entities': 1.1
            },
            'focus': 'Emphasizes content quality, trustworthiness, and natural language'
        },
        'Gemini': {
            'weights': {
                'schema': 1.3,
                'questions': 1.0,
                'snippet': 1.2,
                'structure': 1.0,
                'eeat': 1.0,
                'entities': 1.2
            },
            'focus': 'Strong preference for structured data and entities'
        },
        'Perplexity': {
            'weights': {
                'schema': 1.1,
                'questions': 1.3,
                'snippet': 1.2,
                'structure': 1.0,
                'eeat': 1.2,
                'entities': 1.0
            },
            'focus': 'Optimized for direct answers and source attribution'
        }
    }
    
    engine_scores = {}
    
    for engine_name, config in engines.items():
        weighted_score = 0
        total_weight = 0
        
        for component, values in base_breakdown['breakdown'].items():
            weight = config['weights'].get(component, 1.0)
            weighted_score += (values['score'] / values['max']) * values['max'] * weight
            total_weight += values['max'] * weight
        
        normalized_score = (weighted_score / total_weight) * 100
        engine_scores[engine_name] = {
            'score': min(round(normalized_score, 1), 100),
            'focus': config['focus']
        }
    
    return engine_scores

def generate_prioritized_recommendations(data):
    """Generate comprehensive recommendations with priority levels and detailed implementation steps"""
    recommendations = []
    
    # HIGH PRIORITY - Critical for AEO Success
    
    # Schema Markup - FAQ
    if not data['schema']['faq_present']:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Schema Markup',
            'action': "Implement FAQ Schema Markup",
            'impact': 'Critical for appearing in "People Also Ask" boxes and AI answer engines. FAQ schema allows AI to extract Q&A directly.',
            'effort': 'Medium',
            'steps': [
                '1. Identify 3-5 common questions your page answers',
                '2. Format them as clear question-answer pairs',
                '3. Add JSON-LD FAQ schema to your page <head> or body',
                '4. Test with Google Rich Results Test tool',
                '5. Example: Use schema.org/FAQPage format'
            ],
            'example': '''<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [{
    "@type": "Question",
    "name": "Your question here?",
    "acceptedAnswer": {
      "@type": "Answer",
      "text": "Your answer here"
    }
  }]
}</script>'''
        })
    
    # Question Headings
    if data['questions']['question_headings'] < 3:
        current_count = data['questions']['question_headings']
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Content Structure',
            'action': f"Add More Question-Based Headings (Currently: {current_count}, Target: 5+)",
            'impact': 'Question headings are how AI engines understand what your content answers. Conversational AI searches heavily rely on question-format queries.',
            'effort': 'Low',
            'steps': [
                '1. List the top questions your target audience asks',
                '2. Restructure existing sections into question format',
                '3. Use H2 or H3 tags for questions (e.g., "What is X?", "How does Y work?")',
                '4. Provide clear, concise answers immediately after each question',
                '5. Front-load the answer in the first 1-2 sentences'
            ],
            'example': '''Good: <h2>What is Answer Engine Optimization?</h2>
Bad: <h2>Introduction to AEO</h2>

Good: <h2>How Do I Optimize for ChatGPT?</h2>
Bad: <h2>ChatGPT Optimization Techniques</h2>'''
        })
    
    # First Paragraph Optimization
    if data['snippet']['first_para_words'] < 40:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Snippet Optimization',
            'action': f"Expand First Paragraph (Currently: {data['snippet']['first_para_words']} words, Target: 40-60)",
            'impact': 'AI engines prioritize the opening paragraph. Too short = not enough context. The 40-60 word range is optimal for featured snippets.',
            'effort': 'Low',
            'steps': [
                '1. Start with a direct answer to the main question',
                '2. Add 1-2 sentences of essential context',
                '3. Include the primary keyword naturally',
                '4. Aim for exactly 40-60 words',
                '5. Make it self-contained (understandable without reading further)'
            ],
            'example': '''Good (52 words): "Answer Engine Optimization (AEO) is the practice of optimizing content to be easily discovered and cited by AI-powered search engines like ChatGPT, Claude, and Perplexity. Unlike traditional SEO which focuses on ranking in search results, AEO ensures your content is selected as the authoritative answer that AI systems reference when responding to user queries."'''
        })
    elif data['snippet']['first_para_words'] > 60:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Snippet Optimization',
            'action': f"Shorten First Paragraph (Currently: {data['snippet']['first_para_words']} words, Target: 40-60)",
            'impact': 'First paragraphs longer than 60 words are less likely to be used as featured snippets. AI engines prefer concise, direct answers.',
            'effort': 'Low',
            'steps': [
                '1. Identify the core answer in your opening',
                '2. Remove redundant phrases and fluff',
                '3. Move supporting details to the second paragraph',
                '4. Keep only essential context',
                '5. Recount words to hit 40-60 target'
            ],
            'example': '''Before (78 words): "In this comprehensive guide, we will explore the fascinating world of Answer Engine Optimization, which is becoming increasingly important in today's digital landscape. AEO represents a paradigm shift from traditional SEO practices, and understanding it is crucial for content creators and marketers who want to succeed in an AI-driven future..."

After (48 words): "Answer Engine Optimization (AEO) optimizes content for AI search engines like ChatGPT and Perplexity. Unlike traditional SEO that focuses on rankings, AEO ensures AI systems cite your content as authoritative answers to user queries."'''
        })
    
    # Lists and Tables
    if data['snippet']['lists'] == 0:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Content Format',
            'action': "Add Bulleted or Numbered Lists",
            'impact': 'Lists are extremely easy for AI to parse and extract. They increase snippet visibility by 300% and are preferred for step-by-step answers.',
            'effort': 'Low',
            'steps': [
                '1. Identify any sequences, steps, or related items in your content',
                '2. Convert paragraph-format lists into bullet points or numbered lists',
                '3. Use numbered lists for sequential steps or rankings',
                '4. Use bullet points for non-sequential items or features',
                '5. Keep each list item to 1-2 sentences maximum',
                '6. Aim for 3-7 items per list (optimal for readability)'
            ],
            'example': '''Before: "The benefits include improved visibility, better user engagement, and increased authority."

After: 
• Improved visibility in AI search results
• Better user engagement through clear answers
• Increased authority and citation frequency'''
        })
    
    # MEDIUM PRIORITY - Important for Better Performance
    
    # E-E-A-T - Author
    if not data['eeat']['has_author_meta']:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'E-E-A-T',
            'action': "Add Author Metadata and Credentials",
            'impact': 'Claude and Perplexity heavily weight author credibility. Author info increases trust signals by 40% and is critical for YMYL (Your Money Your Life) content.',
            'effort': 'Low',
            'steps': [
                '1. Add author meta tag: <meta name="author" content="Author Name">',
                '2. Include author byline at top of article with credentials',
                '3. Link to author bio page or LinkedIn profile',
                '4. Add author schema markup with expertise details',
                '5. Include author photo for additional trust'
            ],
            'example': '''<meta name="author" content="Dr. Jane Smith">

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "author": {
    "@type": "Person",
    "name": "Dr. Jane Smith",
    "jobTitle": "AI Research Scientist",
    "url": "https://example.com/author/jane-smith"
  }
}</script>'''
        })
    
    # Publication Date
    if not data['eeat']['has_date']:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'E-E-A-T',
            'action': "Add Publication and Update Dates",
            'impact': 'AI engines prefer recent content. Dates signal freshness and help AI determine if information is current or outdated.',
            'effort': 'Low',
            'steps': [
                '1. Add meta tag: <meta property="article:published_time" content="2024-01-15">',
                '2. Display publication date visibly on page',
                '3. Add "Last Updated" date if content is refreshed',
                '4. Include datePublished and dateModified in Article schema',
                '5. Keep content updated and reflect changes in dates'
            ],
            'example': '''<meta property="article:published_time" content="2024-01-15T10:00:00Z">
<meta property="article:modified_time" content="2024-03-20T14:30:00Z">

Published: January 15, 2024 | Last Updated: March 20, 2024'''
        })
    
    # HowTo Schema
    if not data['schema']['howto_present'] and data['questions']['question_headings'] > 0:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Schema Markup',
            'action': "Implement HowTo Schema for Process Content",
            'impact': 'HowTo schema is perfect for instructional content. It enables step-by-step extraction and increases visibility for "how to" queries by 250%.',
            'effort': 'Medium',
            'steps': [
                '1. Identify if your content includes a process or tutorial',
                '2. Break the process into clear, sequential steps',
                '3. Add HowTo schema with each step defined',
                '4. Include tools/materials needed if applicable',
                '5. Estimate total time for completion',
                '6. Test with Google Rich Results Test'
            ],
            'example': '''<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to Optimize Content for AEO",
  "step": [{
    "@type": "HowToStep",
    "name": "Add Question Headings",
    "text": "Restructure your headings as questions..."
  }, {
    "@type": "HowToStep",
    "name": "Implement Schema Markup",
    "text": "Add FAQ or HowTo schema to your page..."
  }]
}</script>'''
        })
    
    # TL;DR
    if not data['structure']['has_tldr']:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Content Structure',
            'action': "Add TL;DR or Executive Summary",
            'impact': 'A summary section provides AI engines with a quick extraction point. It increases the likelihood of being cited by 180%.',
            'effort': 'Medium',
            'steps': [
                '1. Add a "TL;DR" or "Key Takeaways" section at the top',
                '2. Summarize main points in 3-5 bullet points',
                '3. Each point should be one sentence',
                '4. Place it immediately after the introduction',
                '5. Use bold formatting: <strong>TL;DR:</strong>',
                '6. Make it scannable and self-contained'
            ],
            'example': '''<strong>TL;DR:</strong>
• AEO optimizes content for AI search engines like ChatGPT and Claude
• Focus on question-based headings, structured data, and concise answers
• Schema markup (FAQ, HowTo) increases AI citation by 250%
• First paragraph should be 40-60 words for optimal snippet performance'''
        })
    
    # Tables
    if data['snippet']['tables'] == 0 and data['structure']['word_count'] > 500:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Content Format',
            'action': "Add Comparison Tables or Data Tables",
            'impact': 'Tables are excellent for structured data extraction. AI engines can easily parse and cite table data. Especially effective for comparisons and specifications.',
            'effort': 'Medium',
            'steps': [
                '1. Identify data that can be presented in table format',
                '2. Common table types: comparisons, features, pricing, specifications',
                '3. Use proper HTML table structure with <thead> and <tbody>',
                '4. Include clear column headers',
                '5. Keep tables simple (3-5 columns max for readability)',
                '6. Add table caption for context'
            ],
            'example': '''<table>
  <caption>AEO vs Traditional SEO</caption>
  <thead>
    <tr>
      <th>Aspect</th>
      <th>Traditional SEO</th>
      <th>AEO</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Goal</td>
      <td>Rank in search results</td>
      <td>Be cited by AI engines</td>
    </tr>
    <tr>
      <td>Focus</td>
      <td>Keywords & backlinks</td>
      <td>Direct answers & structure</td>
    </tr>
  </tbody>
</table>'''
        })
    
    # Article Schema
    if not data['schema']['article_present'] and data['structure']['word_count'] > 300:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Schema Markup',
            'action': "Add Article Schema Markup",
            'impact': 'Article schema provides essential metadata that AI engines use to understand and categorize your content.',
            'effort': 'Low',
            'steps': [
                '1. Determine article type (Article, BlogPosting, NewsArticle)',
                '2. Add JSON-LD with headline, description, author, date',
                '3. Include image URL if available',
                '4. Add publisher information',
                '5. Test with Google Rich Results Test'
            ],
            'example': '''<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Complete Guide to AEO",
  "description": "Learn how to optimize content for AI engines",
  "author": {
    "@type": "Person",
    "name": "Jane Smith"
  },
  "datePublished": "2024-01-15"
}</script>'''
        })
    
    # Author Bio
    if not data['eeat']['has_author_bio'] and data['eeat']['has_author_meta']:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'E-E-A-T',
            'action': "Create Author Bio Section",
            'impact': 'An author bio establishes expertise and builds trust. Critical for Claude which emphasizes author credibility.',
            'effort': 'Low',
            'steps': [
                '1. Add author bio section at end of article',
                '2. Include 2-3 sentences about author expertise',
                '3. Mention relevant credentials, experience, or achievements',
                '4. Add link to full author profile or LinkedIn',
                '5. Include professional headshot if possible'
            ],
            'example': '''<div class="author-bio">
  <h3>About the Author</h3>
  <p><strong>Dr. Jane Smith</strong> is an AI Research Scientist with 10 years of experience in natural language processing. She has published 15 peer-reviewed papers on semantic search and advises Fortune 500 companies on AI strategy.</p>
  <a href="/author/jane-smith">View full profile</a>
</div>'''
        })
    
    # LOW PRIORITY - Nice to Have
    
    # Readability
    if data['structure']['flesch_reading_ease'] < 60:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Readability',
            'action': f"Improve Readability Score (Current: {data['structure']['flesch_reading_ease']}, Target: 60+)",
            'impact': 'Higher readability scores mean AI engines can better understand and extract your content. Aim for 8th-9th grade reading level.',
            'effort': 'High',
            'steps': [
                '1. Use shorter sentences (15-20 words average)',
                '2. Replace complex words with simpler alternatives',
                '3. Break up long paragraphs (3-4 sentences max)',
                '4. Use active voice instead of passive voice',
                '5. Add transition words for flow',
                '6. Test with Hemingway Editor or similar tools'
            ],
            'example': '''Before: "The implementation of Answer Engine Optimization methodologies necessitates a comprehensive understanding of the algorithmic processes utilized by contemporary AI-powered search infrastructures."

After: "To optimize for answer engines, you need to understand how modern AI search systems work."'''
        })
    
    # Paragraph Length
    if data['structure']['avg_para_length'] > 100:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Readability',
            'action': f"Shorten Paragraphs (Current avg: {data['structure']['avg_para_length']} words, Target: 50-75)",
            'impact': 'Shorter paragraphs improve scannability and make it easier for AI to identify discrete concepts and extract answers.',
            'effort': 'Medium',
            'steps': [
                '1. Aim for 2-4 sentences per paragraph',
                '2. One main idea per paragraph',
                '3. Use paragraph breaks for better visual flow',
                '4. Split long paragraphs at natural transition points',
                '5. Keep most paragraphs under 75 words'
            ],
            'example': '''Before: One long 150-word paragraph covering multiple ideas.

After: 
Split into 3 shorter paragraphs:
- Paragraph 1: Introduce main concept (50 words)
- Paragraph 2: Explain benefits (60 words)  
- Paragraph 3: Provide example (55 words)'''
        })
    
    # Entities
    if data['entities']['entities_found'] < 10:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Semantic SEO',
            'action': f"Increase Entity Mentions (Current: {data['entities']['entities_found']}, Target: 15+)",
            'impact': 'Entities (proper nouns, brands, people, places) help AI engines understand topic context. Gemini particularly relies on entity recognition.',
            'effort': 'High',
            'steps': [
                '1. Mention relevant brands, products, or companies',
                '2. Reference industry experts or thought leaders',
                '3. Include specific tools, technologies, or methodologies by name',
                '4. Add geographic locations if relevant',
                '5. Use full names on first mention, then abbreviations',
                '6. Link to authoritative sources about these entities'
            ],
            'example': '''Weak: "Many search engines use AI technology."

Strong: "Google's Bard, OpenAI's ChatGPT, Anthropic's Claude, and Perplexity AI all use large language models (LLMs) based on transformer architecture developed by researchers at Google Brain."'''
        })
    
    # Sources
    if not data['eeat']['has_sources']:
        recommendations.append({
            'priority': 'LOW',
            'category': 'E-E-A-T',
            'action': "Add Citations and References Section",
            'impact': 'External citations demonstrate research depth and build credibility. Perplexity specifically values source attribution.',
            'effort': 'Medium',
            'steps': [
                '1. Add "References" or "Sources" section at article end',
                '2. Cite authoritative sources (academic papers, industry reports)',
                '3. Use inline citations or numbered references',
                '4. Link to original sources',
                '5. Prefer .edu, .gov, and reputable industry sites',
                '6. Include publication dates for sources'
            ],
            'example': '''<section class="references">
  <h2>References</h2>
  <ol>
    <li>Smith, J. (2023). "The Future of Search: AI and Semantic Understanding." Journal of Information Science. <a href="#">Link</a></li>
    <li>OpenAI Research Team. (2024). "GPT-4 Technical Report." OpenAI. <a href="#">Link</a></li>
  </ol>
</section>'''
        })
    
    # Table of Contents
    if not data['structure']['has_toc'] and data['structure']['word_count'] > 1500:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Navigation',
            'action': "Add Table of Contents",
            'impact': 'A table of contents helps AI understand content structure and improves user navigation. Especially valuable for long-form content.',
            'effort': 'Low',
            'steps': [
                '1. Create TOC for articles over 1500 words',
                '2. List all H2 and major H3 headings',
                '3. Use jump links (anchor tags) to sections',
                '4. Place TOC after introduction',
                '5. Consider sticky TOC for long articles',
                '6. Use semantic HTML: <nav> tag with aria-label="Table of Contents"'
            ],
            'example': '''<nav aria-label="Table of Contents">
  <h2>Table of Contents</h2>
  <ul>
    <li><a href="#what-is-aeo">What is AEO?</a></li>
    <li><a href="#why-matters">Why AEO Matters</a></li>
    <li><a href="#implementation">How to Implement</a></li>
    <li><a href="#best-practices">Best Practices</a></li>
  </ul>
</nav>'''
        })
    
    # Internal Linking
    if data['structure']['word_count'] > 500:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Content Structure',
            'action': "Add Strategic Internal Links",
            'impact': 'Internal links help AI understand content relationships and site structure. They also guide users to related information.',
            'effort': 'Low',
            'steps': [
                '1. Link to 3-5 related articles on your site',
                '2. Use descriptive anchor text (not "click here")',
                '3. Link to deeper explanation of concepts mentioned',
                '4. Add links naturally within content flow',
                '5. Link to authoritative external sources when appropriate',
                '6. Ensure all links open in new tab for external sites'
            ],
            'example': '''Learn more about <a href="/semantic-seo-guide">semantic SEO strategies</a> to complement your AEO efforts.

For a deeper dive into structured data, see our complete <a href="/schema-markup-tutorial">schema markup tutorial</a>.'''
        })
    
    # Word Count
    if data['structure']['word_count'] < 500:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Content Depth',
            'action': f"Expand Content Depth (Current: {data['structure']['word_count']} words, Target: 800+)",
            'impact': 'Longer, comprehensive content tends to perform better with AI engines. Aim for 800-2000 words for most topics.',
            'effort': 'High',
            'steps': [
                '1. Add more detailed explanations of key concepts',
                '2. Include examples and use cases',
                '3. Address related questions and subtopics',
                '4. Add a "Common Questions" or FAQ section',
                '5. Provide step-by-step instructions where applicable',
                '6. Include expert insights or quotes'
            ],
            'example': '''Expand from basic definition to include:
• What it is (100 words)
• Why it matters (150 words)
• How it works (200 words)
• Implementation steps (250 words)
• Examples (150 words)
• Common mistakes (100 words)
• Resources (50 words)
Total: ~1000 words'''
        })
    
    # Contact Link
    if not data['eeat']['has_contact_link']:
        recommendations.append({
            'priority': 'LOW',
            'category': 'E-E-A-T',
            'action': "Add Contact Page Link",
            'impact': 'A visible contact link builds trust and credibility. Shows you stand behind your content.',
            'effort': 'Low',
            'steps': [
                '1. Add contact link in header or footer navigation',
                '2. Create dedicated contact page with form or email',
                '3. Include social media profiles',
                '4. Add physical address if you have a business location',
                '5. Ensure contact page is linked from every article'
            ],
            'example': '''<footer>
  <nav>
    <a href="/about">About</a>
    <a href="/contact">Contact</a>
    <a href="/privacy">Privacy</a>
  </nav>
</footer>'''
        })
    
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    recommendations.sort(key=lambda x: priority_order[x['priority']])
    
    return recommendations

# Main App
st.markdown('<p class="main-header">🎯 AEO On-Page Auditor</p>', unsafe_allow_html=True)
st.markdown("**Analyze your webpage for Answer Engine Optimization (AEO)** - optimize for AI search engines, featured snippets, and voice search.")

# Main App
st.markdown('<p class="main-header">🎯 AEO On-Page Auditor</p>', unsafe_allow_html=True)
st.markdown("**Analyze your webpage for Answer Engine Optimization (AEO)** - optimize for AI search engines, featured snippets, and voice search.")

# Tabs for single vs comparison analysis
tab1, tab2 = st.tabs(["📄 Single Page Analysis", "⚔️ Competitive Comparison"])

with tab1:
    # Input
    url = st.text_input("Enter URL to Analyze", placeholder="https://example.com/article", key="single_url")

    if st.button("🔍 Analyze", type="primary", use_container_width=True, key="analyze_single"):
        if not url:
            st.error("Please enter a URL")
        else:
            with st.spinner("Analyzing webpage..."):
                try:
                    # Fetch and analyze
                    html = fetch_page(url)
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    schema_data = analyze_schema(soup)
                    question_data = analyze_questions(soup)
                    snippet_data = analyze_snippet_optimization(soup)
                    structure_data = analyze_structure(soup)
                    entity_data = analyze_entities(soup)
                    eeat_data = analyze_eeat(soup, url)
                    
                    result = {
                        'schema': schema_data,
                        'questions': question_data,
                        'snippet': snippet_data,
                        'structure': structure_data,
                        'entities': entity_data,
                        'eeat': eeat_data
                    }
                    
                    score_breakdown = calculate_score_breakdown(result)
                    engine_scores = calculate_engine_scores(result)
                    recommendations = generate_prioritized_recommendations(result)
                    
                    # Display Results
                    st.success(f"✅ Analysis complete for: {url}")
                    
                    # Overall Score
                    aeo_score = score_breakdown['total']
                    score_class = "score-high" if aeo_score >= 80 else "score-medium" if aeo_score >= 60 else "score-low"
                    
                    st.markdown(f"""
                    <div class="score-card {score_class}">
                        <h2>Overall AEO Score</h2>
                        <h1 style="font-size: 4rem; margin: 1rem 0;">{aeo_score}</h1>
                        <p>out of 100</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Quick Checks
                    st.subheader("✓ Quick Checks")
                    col1, col2, col3 = st.columns(3)
                    
                    checks = {
                        'FAQ Schema': schema_data['faq_present'],
                        'HowTo Schema': schema_data['howto_present'],
                        'Question Headings': question_data['question_headings'] >= 3,
                        'Snippet Ready': snippet_data['snippet_score'] >= 50,
                        'Has TL;DR': structure_data['has_tldr'],
                        'Good Readability': structure_data['flesch_reading_ease'] >= 60,
                        'Author Info': eeat_data['has_author_meta']
                    }
                    
                    for i, (check, passed) in enumerate(checks.items()):
                        col = [col1, col2, col3][i % 3]
                        icon = "✅" if passed else "❌"
                        col.metric(check, icon)
                    
                    # Engine Scores
                    st.subheader("🤖 Score by Answer Engine")
                    st.markdown("Different AI engines prioritize different content factors.")
                    
                    cols = st.columns(2)
                    for i, (engine, data) in enumerate(engine_scores.items()):
                        with cols[i % 2]:
                            score = data['score']
                            st.metric(engine, f"{score}/100")
                            st.caption(data['focus'])
                            st.progress(score / 100)
                    
                    # Score Breakdown
                    st.subheader("📊 Score Breakdown by Component")
                    
                    component_names = {
                        'schema': 'Schema Markup',
                        'questions': 'Question Content',
                        'snippet': 'Snippet Optimization',
                        'structure': 'Content Structure',
                        'eeat': 'E-E-A-T Signals',
                        'entities': 'Entity Recognition'
                    }
                    
                    for component, values in score_breakdown['breakdown'].items():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{component_names[component]}**")
                            st.progress(values['score'] / values['max'])
                        with col2:
                            st.write(f"{values['score']}/{values['max']}")
                    
                    # Prioritized Recommendations
                    st.subheader("⚠️ Prioritized Recommendations")
                    st.markdown(f"**{len(recommendations)} actionable improvements identified**")
                    
                    # Priority filter
                    priority_filter = st.radio(
                        "Filter by priority:",
                        ["All", "HIGH", "MEDIUM", "LOW"],
                        horizontal=True
                    )
                    
                    filtered_recs = recommendations if priority_filter == "All" else [r for r in recommendations if r['priority'] == priority_filter]
                    
                    for i, rec in enumerate(filtered_recs):
                        priority_class = f"priority-{rec['priority'].lower()}"
                        
                        with st.expander(f"{'🔴' if rec['priority'] == 'HIGH' else '🟡' if rec['priority'] == 'MEDIUM' else '🔵'} **{rec['action']}**", expanded=(i < 3)):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.markdown(f"**Priority:** {rec['priority']}")
                                st.markdown(f"**Category:** {rec['category']}")
                                st.markdown(f"**Effort:** {rec['effort']}")
                            
                            with col2:
                                pass
                            
                            st.markdown("---")
                            st.markdown(f"**💡 Why This Matters:**")
                            st.info(rec['impact'])
                            
                            if 'steps' in rec:
                                st.markdown("**📋 Implementation Steps:**")
                                for step in rec['steps']:
                                    st.markdown(step)
                            
                            if 'example' in rec:
                                st.markdown("**📝 Code Example:**")
                                st.code(rec['example'], language='html')
                    
                    # Detailed Metrics
                    st.subheader("📋 Detailed Metrics")
                    
                    tab1, tab2, tab3, tab4 = st.tabs(["Schema", "Snippet", "Structure", "E-E-A-T"])
                    
                    with tab1:
                        st.write(f"**FAQ Schema:** {'Yes (' + str(schema_data['faq_count']) + ' items)' if schema_data['faq_present'] else 'No'}")
                        st.write(f"**HowTo Schema:** {'Yes (' + str(schema_data['howto_count']) + ' steps)' if schema_data['howto_present'] else 'No'}")
                        st.write(f"**Article Schema:** {'Yes' if schema_data['article_present'] else 'No'}")
                    
                    with tab2:
                        st.write(f"**First Paragraph:** {snippet_data['first_para_words']} words")
                        st.write(f"**Lists:** {snippet_data['lists']}")
                        st.write(f"**Tables:** {snippet_data['tables']}")
                        st.write(f"**Snippet Score:** {snippet_data['snippet_score']}/100")
                    
                    with tab3:
                        st.write(f"**Word Count:** {structure_data['word_count']}")
                        st.write(f"**Question Headings:** {question_data['question_headings']}/{question_data['total_headings']}")
                        st.write(f"**Readability Score:** {structure_data['flesch_reading_ease']}")
                        st.write(f"**Has TL;DR:** {'Yes' if structure_data['has_tldr'] else 'No'}")
                        
                        if question_data['question_heading_examples']:
                            st.write("**Question Headings Found:**")
                            for q in question_data['question_heading_examples']:
                                st.write(f"- {q}")
                    
                    with tab4:
                        st.write(f"**Author Meta:** {'Yes' if eeat_data['has_author_meta'] else 'No'}")
                        st.write(f"**Publication Date:** {'Yes' if eeat_data['has_date'] else 'No'}")
                        st.write(f"**Author Bio:** {'Yes' if eeat_data['has_author_bio'] else 'No'}")
                        st.write(f"**Sources/References:** {'Yes' if eeat_data['has_sources'] else 'No'}")
                    
                except Exception as e:
                    st.error(f"Error analyzing URL: {str(e)}")
                    st.info("Make sure the URL is accessible and returns valid HTML content.")

with tab2:
    st.markdown("### Compare Your Page Against Competitors")
    st.markdown("Analyze up to 4 pages simultaneously to see how you stack up against the competition.")
    
    # Input fields for comparison
    col1, col2 = st.columns(2)
    
    with col1:
        your_url = st.text_input("🏠 Your URL", placeholder="https://your-site.com/article", key="your_url")
        competitor2_url = st.text_input("🔗 Competitor 2 (Optional)", placeholder="https://competitor2.com/article", key="comp2")
    
    with col2:
        competitor1_url = st.text_input("🔗 Competitor 1", placeholder="https://competitor1.com/article", key="comp1")
        competitor3_url = st.text_input("🔗 Competitor 3 (Optional)", placeholder="https://competitor3.com/article", key="comp3")
    
    if st.button("⚔️ Compare All", type="primary", use_container_width=True, key="compare_btn"):
        urls_to_compare = {
            "Your Site": your_url,
            "Competitor 1": competitor1_url,
            "Competitor 2": competitor2_url,
            "Competitor 3": competitor3_url
        }
        
        # Filter out empty URLs
        urls_to_compare = {k: v for k, v in urls_to_compare.items() if v.strip()}
        
        if len(urls_to_compare) < 2:
            st.error("Please enter at least 2 URLs to compare (Your URL + at least 1 competitor)")
        else:
            results_dict = {}
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, (name, url) in enumerate(urls_to_compare.items()):
                status_text.text(f"Analyzing {name}...")
                progress_bar.progress((idx + 1) / len(urls_to_compare))
                
                try:
                    html = fetch_page(url)
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    schema_data = analyze_schema(soup)
                    question_data = analyze_questions(soup)
                    snippet_data = analyze_snippet_optimization(soup)
                    structure_data = analyze_structure(soup)
                    entity_data = analyze_entities(soup)
                    eeat_data = analyze_eeat(soup, url)
                    
                    result = {
                        'url': url,
                        'schema': schema_data,
                        'questions': question_data,
                        'snippet': snippet_data,
                        'structure': structure_data,
                        'entities': entity_data,
                        'eeat': eeat_data
                    }
                    
                    score_breakdown = calculate_score_breakdown(result)
                    engine_scores = calculate_engine_scores(result)
                    
                    results_dict[name] = {
                        'url': url,
                        'overall_score': score_breakdown['total'],
                        'breakdown': score_breakdown['breakdown'],
                        'engine_scores': engine_scores,
                        'raw_data': result
                    }
                    
                except Exception as e:
                    st.warning(f"Could not analyze {name}: {str(e)}")
                    continue
            
            progress_bar.empty()
            status_text.empty()
            
            if len(results_dict) >= 2:
                st.success(f"✅ Successfully analyzed {len(results_dict)} pages!")
                
                # Overall Score Comparison
                st.subheader("🏆 Overall AEO Score Comparison")
                
                score_data = {name: data['overall_score'] for name, data in results_dict.items()}
                
                # Create bar chart
                fig = go.Figure(data=[
                    go.Bar(
                        x=list(score_data.keys()),
                        y=list(score_data.values()),
                        text=list(score_data.values()),
                        textposition='auto',
                        marker_color=['#10B981' if name == "Your Site" else '#6366F1' for name in score_data.keys()]
                    )
                ])
                
                fig.update_layout(
                    title="Overall AEO Scores",
                    xaxis_title="Website",
                    yaxis_title="Score (out of 100)",
                    yaxis_range=[0, 100],
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Score table
                col1, col2 = st.columns([2, 1])
                with col1:
                    score_df = pd.DataFrame([
                        {'Website': name, 'AEO Score': score, 'Rank': idx + 1}
                        for idx, (name, score) in enumerate(sorted(score_data.items(), key=lambda x: x[1], reverse=True))
                    ])
                    st.dataframe(score_df, hide_index=True, use_container_width=True)
                
                with col2:
                    if "Your Site" in score_data:
                        your_score = score_data["Your Site"]
                        competitor_scores = [s for n, s in score_data.items() if n != "Your Site"]
                        avg_competitor = sum(competitor_scores) / len(competitor_scores)
                        difference = your_score - avg_competitor
                        
                        st.metric(
                            "Your Score vs Avg Competitor",
                            f"{your_score}",
                            f"{difference:+.1f} points",
                            delta_color="normal" if difference > 0 else "inverse"
                        )
                
                # Component Breakdown Comparison
                st.subheader("📊 Component Breakdown Comparison")
                
                component_names = {
                    'schema': 'Schema Markup',
                    'questions': 'Question Content',
                    'snippet': 'Snippet Optimization',
                    'structure': 'Content Structure',
                    'eeat': 'E-E-A-T Signals',
                    'entities': 'Entity Recognition'
                }
                
                # Prepare data for radar chart
                categories = list(component_names.values())
                
                fig = go.Figure()
                
                for name, data in results_dict.items():
                    scores = []
                    for comp in component_names.keys():
                        percentage = (data['breakdown'][comp]['score'] / data['breakdown'][comp]['max']) * 100
                        scores.append(percentage)
                    
                    fig.add_trace(go.Scatterpolar(
                        r=scores,
                        theta=categories,
                        fill='toself',
                        name=name,
                        line=dict(width=2)
                    ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100]
                        )
                    ),
                    showlegend=True,
                    height=500,
                    title="Component Performance Radar"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed component comparison table
                st.subheader("📋 Detailed Component Scores")
                
                comparison_data = []
                for comp_key, comp_name in component_names.items():
                    row = {'Component': comp_name}
                    for name, data in results_dict.items():
                        score = data['breakdown'][comp_key]['score']
                        max_score = data['breakdown'][comp_key]['max']
                        row[name] = f"{score}/{max_score}"
                    comparison_data.append(row)
                
                comp_df = pd.DataFrame(comparison_data)
                st.dataframe(comp_df, hide_index=True, use_container_width=True)
                
                # Engine-Specific Scores
                st.subheader("🤖 AI Engine Scores Comparison")
                
                engines = ['ChatGPT', 'Claude', 'Gemini', 'Perplexity']
                
                fig = go.Figure()
                
                for name, data in results_dict.items():
                    engine_values = [data['engine_scores'][engine]['score'] for engine in engines]
                    fig.add_trace(go.Bar(
                        name=name,
                        x=engines,
                        y=engine_values,
                        text=engine_values,
                        textposition='auto'
                    ))
                
                fig.update_layout(
                    title="AI Engine Performance Comparison",
                    xaxis_title="AI Engine",
                    yaxis_title="Score",
                    barmode='group',
                    height=400,
                    yaxis_range=[0, 100]
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Key Metrics Comparison
                st.subheader("🔍 Key Metrics Comparison")
                
                metrics_data = []
                for name, data in results_dict.items():
                    raw = data['raw_data']
                    metrics_data.append({
                        'Website': name,
                        'FAQ Schema': '✅' if raw['schema']['faq_present'] else '❌',
                        'HowTo Schema': '✅' if raw['schema']['howto_present'] else '❌',
                        'Word Count': raw['structure']['word_count'],
                        'Question Headings': f"{raw['questions']['question_headings']}/{raw['questions']['total_headings']}",
                        'Lists': raw['snippet']['lists'],
                        'Tables': raw['snippet']['tables'],
                        'Readability': raw['structure']['flesch_reading_ease'],
                        'Author Info': '✅' if raw['eeat']['has_author_meta'] else '❌',
                        'Has TL;DR': '✅' if raw['structure']['has_tldr'] else '❌'
                    })
                
                metrics_df = pd.DataFrame(metrics_data)
                st.dataframe(metrics_df, hide_index=True, use_container_width=True)
                
                # Competitive Gap Analysis
                if "Your Site" in results_dict:
                    st.subheader("📈 Your Competitive Gaps")
                    st.markdown("Areas where competitors are outperforming you:")
                    
                    gaps = []
                    your_data = results_dict["Your Site"]['raw_data']
                    
                    # Check each metric against competitors
                    for name, comp_data in results_dict.items():
                        if name == "Your Site":
                            continue
                        
                        comp_raw = comp_data['raw_data']
                        
                        # FAQ Schema gap
                        if not your_data['schema']['faq_present'] and comp_raw['schema']['faq_present']:
                            gaps.append(f"❌ **FAQ Schema**: {name} has FAQ schema, you don't")
                        
                        # HowTo Schema gap
                        if not your_data['schema']['howto_present'] and comp_raw['schema']['howto_present']:
                            gaps.append(f"❌ **HowTo Schema**: {name} has HowTo schema, you don't")
                        
                        # Question headings gap
                        if your_data['questions']['question_headings'] < comp_raw['questions']['question_headings']:
                            gap = comp_raw['questions']['question_headings'] - your_data['questions']['question_headings']
                            gaps.append(f"⚠️ **Question Headings**: {name} has {gap} more question-based headings")
                        
                        # Lists gap
                        if your_data['snippet']['lists'] < comp_raw['snippet']['lists']:
                            gap = comp_raw['snippet']['lists'] - your_data['snippet']['lists']
                            gaps.append(f"⚠️ **Lists**: {name} has {gap} more lists")
                        
                        # Word count gap (if significantly different)
                        if your_data['structure']['word_count'] < comp_raw['structure']['word_count'] * 0.7:
                            gaps.append(f"⚠️ **Content Depth**: {name} has {comp_raw['structure']['word_count']} words vs your {your_data['structure']['word_count']}")
                        
                        # Author info gap
                        if not your_data['eeat']['has_author_meta'] and comp_raw['eeat']['has_author_meta']:
                            gaps.append(f"❌ **Author Info**: {name} has author metadata, you don't")
                    
                    if gaps:
                        for gap in list(set(gaps))[:10]:  # Show unique gaps, max 10
                            st.markdown(gap)
                    else:
                        st.success("🎉 You're competitive across all major metrics!")
                
                # Best Practices from Competitors
                st.subheader("💡 Best Practices from Top Performers")
                
                # Find the highest scoring competitor
                top_performer = max(
                    [(name, data['overall_score']) for name, data in results_dict.items()],
                    key=lambda x: x[1]
                )
                
                st.info(f"**Top Performer: {top_performer[0]}** with a score of {top_performer[1]}/100")
                
                top_data = results_dict[top_performer[0]]['raw_data']
                best_practices = []
                
                if top_data['schema']['faq_present']:
                    best_practices.append(f"✅ Uses FAQ Schema with {top_data['schema']['faq_count']} questions")
                if top_data['schema']['howto_present']:
                    best_practices.append(f"✅ Implements HowTo Schema with {top_data['schema']['howto_count']} steps")
                if top_data['structure']['has_tldr']:
                    best_practices.append("✅ Includes TL;DR summary section")
                if top_data['snippet']['lists'] > 2:
                    best_practices.append(f"✅ Uses {top_data['snippet']['lists']} lists for better readability")
                if top_data['questions']['question_headings'] >= 5:
                    best_practices.append(f"✅ Has {top_data['questions']['question_headings']} question-based headings")
                if top_data['eeat']['has_author_meta']:
                    best_practices.append("✅ Includes comprehensive author information")
                if top_data['structure']['flesch_reading_ease'] >= 60:
                    best_practices.append(f"✅ Maintains good readability (score: {top_data['structure']['flesch_reading_ease']})")
                
                for practice in best_practices:
                    st.markdown(practice)
            
            else:
                st.error("Could not analyze enough pages for comparison. Please check the URLs and try again.")

# Input
url = st.text_input("Enter URL to Analyze", placeholder="https://example.com/article")

if st.button("🔍 Analyze", type="primary", use_container_width=True):
    if not url:
        st.error("Please enter a URL")
    else:
        with st.spinner("Analyzing webpage..."):
            try:
                # Fetch and analyze
                html = fetch_page(url)
                soup = BeautifulSoup(html, 'html.parser')
                
                schema_data = analyze_schema(soup)
                question_data = analyze_questions(soup)
                snippet_data = analyze_snippet_optimization(soup)
                structure_data = analyze_structure(soup)
                entity_data = analyze_entities(soup)
                eeat_data = analyze_eeat(soup, url)
                
                result = {
                    'schema': schema_data,
                    'questions': question_data,
                    'snippet': snippet_data,
                    'structure': structure_data,
                    'entities': entity_data,
                    'eeat': eeat_data
                }
                
                score_breakdown = calculate_score_breakdown(result)
                engine_scores = calculate_engine_scores(result)
                recommendations = generate_prioritized_recommendations(result)
                
                # Display Results
                st.success(f"✅ Analysis complete for: {url}")
                
                # Overall Score
                aeo_score = score_breakdown['total']
                score_class = "score-high" if aeo_score >= 80 else "score-medium" if aeo_score >= 60 else "score-low"
                
                st.markdown(f"""
                <div class="score-card {score_class}">
                    <h2>Overall AEO Score</h2>
                    <h1 style="font-size: 4rem; margin: 1rem 0;">{aeo_score}</h1>
                    <p>out of 100</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Quick Checks
                st.subheader("✓ Quick Checks")
                col1, col2, col3 = st.columns(3)
                
                checks = {
                    'FAQ Schema': schema_data['faq_present'],
                    'HowTo Schema': schema_data['howto_present'],
                    'Question Headings': question_data['question_headings'] >= 3,
                    'Snippet Ready': snippet_data['snippet_score'] >= 50,
                    'Has TL;DR': structure_data['has_tldr'],
                    'Good Readability': structure_data['flesch_reading_ease'] >= 60,
                    'Author Info': eeat_data['has_author_meta']
                }
                
                for i, (check, passed) in enumerate(checks.items()):
                    col = [col1, col2, col3][i % 3]
                    icon = "✅" if passed else "❌"
                    col.metric(check, icon)
                
                # Engine Scores
                st.subheader("🤖 Score by Answer Engine")
                st.markdown("Different AI engines prioritize different content factors.")
                
                cols = st.columns(2)
                for i, (engine, data) in enumerate(engine_scores.items()):
                    with cols[i % 2]:
                        score = data['score']
                        st.metric(engine, f"{score}/100")
                        st.caption(data['focus'])
                        st.progress(score / 100)
                
                # Score Breakdown
                st.subheader("📊 Score Breakdown by Component")
                
                component_names = {
                    'schema': 'Schema Markup',
                    'questions': 'Question Content',
                    'snippet': 'Snippet Optimization',
                    'structure': 'Content Structure',
                    'eeat': 'E-E-A-T Signals',
                    'entities': 'Entity Recognition'
                }
                
                for component, values in score_breakdown['breakdown'].items():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{component_names[component]}**")
                        st.progress(values['score'] / values['max'])
                    with col2:
                        st.write(f"{values['score']}/{values['max']}")
                
                # Prioritized Recommendations
                st.subheader("⚠️ Prioritized Recommendations")
                st.markdown(f"**{len(recommendations)} actionable improvements identified**")
                
                # Priority filter
                priority_filter = st.radio(
                    "Filter by priority:",
                    ["All", "HIGH", "MEDIUM", "LOW"],
                    horizontal=True
                )
                
                filtered_recs = recommendations if priority_filter == "All" else [r for r in recommendations if r['priority'] == priority_filter]
                
                for i, rec in enumerate(filtered_recs):
                    priority_class = f"priority-{rec['priority'].lower()}"
                    
                    with st.expander(f"{'🔴' if rec['priority'] == 'HIGH' else '🟡' if rec['priority'] == 'MEDIUM' else '🔵'} **{rec['action']}**", expanded=(i < 3)):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**Priority:** {rec['priority']}")
                            st.markdown(f"**Category:** {rec['category']}")
                            st.markdown(f"**Effort:** {rec['effort']}")
                        
                        with col2:
                            pass
                        
                        st.markdown("---")
                        st.markdown(f"**💡 Why This Matters:**")
                        st.info(rec['impact'])
                        
                        if 'steps' in rec:
                            st.markdown("**📋 Implementation Steps:**")
                            for step in rec['steps']:
                                st.markdown(step)
                        
                        if 'example' in rec:
                            st.markdown("**📝 Code Example:**")
                            st.code(rec['example'], language='html')
                
                # Detailed Metrics
                st.subheader("📋 Detailed Metrics")
                
                tab1, tab2, tab3, tab4 = st.tabs(["Schema", "Snippet", "Structure", "E-E-A-T"])
                
                with tab1:
                    st.write(f"**FAQ Schema:** {'Yes (' + str(schema_data['faq_count']) + ' items)' if schema_data['faq_present'] else 'No'}")
                    st.write(f"**HowTo Schema:** {'Yes (' + str(schema_data['howto_count']) + ' steps)' if schema_data['howto_present'] else 'No'}")
                    st.write(f"**Article Schema:** {'Yes' if schema_data['article_present'] else 'No'}")
                
                with tab2:
                    st.write(f"**First Paragraph:** {snippet_data['first_para_words']} words")
                    st.write(f"**Lists:** {snippet_data['lists']}")
                    st.write(f"**Tables:** {snippet_data['tables']}")
                    st.write(f"**Snippet Score:** {snippet_data['snippet_score']}/100")
                
                with tab3:
                    st.write(f"**Word Count:** {structure_data['word_count']}")
                    st.write(f"**Question Headings:** {question_data['question_headings']}/{question_data['total_headings']}")
                    st.write(f"**Readability Score:** {structure_data['flesch_reading_ease']}")
                    st.write(f"**Has TL;DR:** {'Yes' if structure_data['has_tldr'] else 'No'}")
                    
                    if question_data['question_heading_examples']:
                        st.write("**Question Headings Found:**")
                        for q in question_data['question_heading_examples']:
                            st.write(f"- {q}")
                
                with tab4:
                    st.write(f"**Author Meta:** {'Yes' if eeat_data['has_author_meta'] else 'No'}")
                    st.write(f"**Publication Date:** {'Yes' if eeat_data['has_date'] else 'No'}")
                    st.write(f"**Author Bio:** {'Yes' if eeat_data['has_author_bio'] else 'No'}")
                    st.write(f"**Sources/References:** {'Yes' if eeat_data['has_sources'] else 'No'}")
                
            except Exception as e:
                st.error(f"Error analyzing URL: {str(e)}")
                st.info("Make sure the URL is accessible and returns valid HTML content.")

# Footer
st.markdown("---")
st.markdown("**AEO On-Page Auditor** | Optimize your content for AI search engines like ChatGPT, Claude, Gemini, and Perplexity")
st.markdown("**Pro Tip:** Use the Competitive Comparison tab to benchmark against your top competitors and identify gaps in your AEO strategy.")