"""
Mind-map generator for paper visualization
Uses LLM to understand and extract paper structure accurately
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import graphviz
from collections import Counter
import os
import json

logger = logging.getLogger(__name__)

# Try to import HTTP client for local LLM
import httpx


class PaperMindMapGenerator:
    """Generate methodology-focused mind-maps from papers"""

    def __init__(self):
        self.section_patterns = {
            'introduction': r'\n\s*(?:1\.|I\.?|Introduction)\s*\n',
            'methodology': r'\n\s*(?:\d+\.|II+\.?)\s*(?:Method|Methodology|Approach|Framework|Algorithm|Materials and Methods)\s*\n',
            'results': r'\n\s*(?:\d+\.|III+\.?|IV+\.?)\s*(?:Result|Findings|Experiments|Evaluation)\s*\n',
            'discussion': r'\n\s*(?:\d+\.|IV+\.?|V+\.?)\s*(?:Discussion|Analysis|Conclusion)\s*\n',
            'related_work': r'\n\s*(?:\d+\.|II\.?)\s*(?:Related Work|Background|Literature Review)\s*\n'
        }

        # Find and set Graphviz executable path
        import shutil
        dot_path = shutil.which('dot')
        if dot_path:
            # Set the executable path for graphviz
            os.environ['PATH'] = os.path.dirname(dot_path) + os.pathsep + os.environ.get('PATH', '')
            logger.info(f"Graphviz dot executable found at: {dot_path}")
        else:
            # Try common installation paths
            common_paths = [
                '/opt/homebrew/bin',
                '/usr/local/bin',
                '/usr/bin'
            ]
            for path in common_paths:
                if os.path.exists(os.path.join(path, 'dot')):
                    os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')
                    logger.info(f"Graphviz dot executable found at: {path}/dot")
                    break
            else:
                logger.warning("Graphviz dot executable not found. SVG generation may fail.")

        # Check if Ollama is available (free local LLM)
        self.ollama_available = False
        self.ollama_url = "http://localhost:11434"
        try:
            # Quick check if Ollama is running
            import requests
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=1)
            if response.status_code == 200:
                self.ollama_available = True
                logger.info("Ollama local LLM detected - will use for mind-map generation")
        except:
            logger.info("Ollama not detected. Install from https://ollama.ai for free LLM-based mind-maps")

    async def generate_mindmap(
        self,
        paper_id: int,
        paper_title: str,
        abstract: str,
        full_text: str,
        include_methodology: bool = True,
        include_results: bool = True,
        include_contributions: bool = True,
        max_depth: int = 3
    ) -> Dict:
        """
        Generate mind-map from paper using LLM for better accuracy

        Args:
            paper_id: Paper ID
            paper_title: Paper title
            abstract: Paper abstract
            full_text: Full paper text
            include_methodology: Include methodology analysis
            include_results: Include results analysis
            include_contributions: Include contributions
            max_depth: Maximum depth of mind-map

        Returns:
            Mind-map data with nodes, SVG, and comprehensive summary
        """
        logger.info(f"Generating mind-map for paper: {paper_title[:50]}...")

        # Try local LLM-based analysis first (free!)
        if self.ollama_available and abstract:
            try:
                structure = await self._analyze_paper_with_ollama(
                    paper_title, abstract, full_text
                )
                logger.info("Successfully generated mind-map using Ollama")
            except Exception as e:
                logger.warning(f"Ollama analysis failed: {e}. Falling back to rule-based extraction.")
                structure = self.analyze_paper_structure(paper_title, abstract, full_text)
        else:
            # Fallback to rule-based extraction
            structure = self.analyze_paper_structure(paper_title, abstract, full_text)

        # Build mind-map tree
        root_node = self._build_mindmap_tree(
            structure,
            include_methodology,
            include_results,
            include_contributions,
            max_depth
        )

        # Generate visualization
        svg_data = self._generate_graphviz_svg(paper_title, root_node)

        # Generate comprehensive summary using LLM
        summary = ""
        if self.ollama_available and abstract:
            try:
                summary = await self._generate_comprehensive_summary(
                    paper_title, abstract, full_text, structure
                )
                logger.info("Successfully generated comprehensive summary")
            except Exception as e:
                logger.warning(f"Summary generation failed: {e}")
                summary = abstract  # Fallback to abstract

        return {
            'paper_id': paper_id,
            'paper_title': paper_title,
            'root_node': root_node,
            'svg_data': svg_data,
            'summary': summary
        }

    async def _analyze_paper_with_ollama(
        self,
        title: str,
        abstract: str,
        full_text: str
    ) -> Dict:
        """Use Ollama (local, free LLM) to accurately extract paper structure with retries"""

        # Prepare comprehensive text - use MORE content for better analysis
        text_to_analyze = f"Title: {title}\n\nAbstract: {abstract}"
        if full_text and len(full_text) > 100:
            # Use up to 10000 chars for detailed analysis (was 4000)
            text_to_analyze += f"\n\nFull text excerpt: {full_text[:10000]}"

        # Enhanced, analytical extraction prompt
        prompt = f"""You are an expert research scientist analyzing this paper. Provide insights and analysis, not just extraction.

Paper:
{text_to_analyze}

Analyze and synthesize the following in valid JSON format:
{{
  "problem": ["Statement 1 explaining the core challenge", "Statement 2 about why this matters", ...],
  "contributions": ["Innovation 1 with explanation of novelty", "Contribution 2 and its significance", ...],
  "methodology": {{
    "key_techniques": ["Technique 1 and how it works", "Technique 2 and why it's effective", ...]
  }},
  "results": ["Finding 1 with interpretation", "Result 2 and its implications", ...],
  "datasets": ["Dataset 1", "Dataset 2", ...]
}}

Requirements:
- Synthesize and explain, don't just copy sentences
- Explain WHY things matter and HOW they work
- Connect ideas and show relationships
- Be specific with technical details
- Use clear, insightful language
- 3-8 items per category
- Valid JSON only

JSON:"""

        # Retry logic - up to 3 attempts
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:  # Increased timeout to 90s
                    response = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": "llama3.2:3b",
                            "prompt": prompt,
                            "stream": False,
                            "format": "json",
                            "options": {
                                "temperature": 0.5,  # Higher for creative synthesis while staying grounded
                                "num_predict": 2500,  # Increased token limit for longer output
                                "num_ctx": 8192  # Increased context window
                            }
                        }
                    )

                if response.status_code != 200:
                    logger.warning(f"Ollama request failed (attempt {attempt + 1}): {response.status_code}")
                    if attempt < 2:
                        continue
                    raise Exception(f"Ollama request failed after 3 attempts: {response.status_code}")

                # Parse response
                ollama_response = response.json()
                response_data = ollama_response.get('response', '{}')

                # Handle response - ensure it's a string
                if isinstance(response_data, dict):
                    # If response is already a dict, convert to JSON string
                    result_text = json.dumps(response_data)
                else:
                    # Clean up response if needed
                    result_text = str(response_data).strip()
                if not result_text.startswith('{'):
                    # Try to find JSON in the response
                    json_start = result_text.find('{')
                    if json_start != -1:
                        result_text = result_text[json_start:]

                try:
                    result = json.loads(result_text)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse error (attempt {attempt + 1}): {e}")
                    if attempt < 2:
                        continue
                    # If all attempts fail, return empty structure
                    result = {}

                # Validate and convert to our structure format
                structure = {
                    'title': title,
                    'abstract_sentences': abstract.split('. ') if abstract else [],
                    'problem': result.get('problem', []) if isinstance(result.get('problem'), list) else [],
                    'contributions': result.get('contributions', []) if isinstance(result.get('contributions'), list) else [],
                    'methodology': {
                        'steps': [],
                        'algorithms': result.get('methodology', {}).get('key_techniques', []) if isinstance(result.get('methodology'), dict) else [],
                        'models': [],
                        'data_processing': []
                    },
                    'techniques': result.get('methodology', {}).get('key_techniques', []) if isinstance(result.get('methodology'), dict) else [],
                    'results': result.get('results', []) if isinstance(result.get('results'), list) else [],
                    'datasets': result.get('datasets', []) if isinstance(result.get('datasets'), list) else []
                }

                # Ensure we have meaningful content
                total_items = (len(structure['problem']) + len(structure['contributions']) +
                              len(structure['techniques']) + len(structure['results']))

                if total_items < 3:  # If too little extracted, retry
                    logger.warning(f"Insufficient content extracted (attempt {attempt + 1}), retrying...")
                    if attempt < 2:
                        continue

                logger.info(f"Successfully extracted: {total_items} items from paper")
                return structure

            except Exception as e:
                logger.warning(f"Ollama analysis attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    continue
                raise

        # Should not reach here, but return empty structure as fallback
        return {
            'title': title,
            'abstract_sentences': abstract.split('. ') if abstract else [],
            'problem': [],
            'contributions': [],
            'methodology': {'steps': [], 'algorithms': [], 'models': [], 'data_processing': []},
            'techniques': [],
            'results': [],
            'datasets': []
        }

    async def _generate_comprehensive_summary(
        self,
        title: str,
        abstract: str,
        full_text: str,
        structure: Dict
    ) -> str:
        """
        Generate a comprehensive, human-readable summary of the paper using LLM with retry logic

        Args:
            title: Paper title
            abstract: Paper abstract
            full_text: Full paper text
            structure: Extracted structure from analysis

        Returns:
            Comprehensive summary as formatted text
        """
        # Prepare comprehensive text for detailed summary - use MORE text
        text_to_analyze = f"Title: {title}\n\nAbstract: {abstract}"
        if full_text and len(full_text) > 100:
            text_to_analyze += f"\n\nFull text excerpt: {full_text[:8000]}"  # Increased to 8000 chars

        # Comprehensive, analytical summary prompt
        prompt = f"""You are an expert research scientist explaining this paper to a colleague. Provide thoughtful analysis and insights.

{text_to_analyze}

Write a comprehensive summary that analyzes and interprets the research:

**📋 Overview**
Explain what this research is fundamentally about and its broader significance. What makes this work interesting or important in its field?

**🎯 Problem & Motivation**
Analyze the core challenge being addressed. Why does this problem matter? What gaps or limitations in existing work motivated this research? What's at stake?

**💡 Key Contributions**
Explain the main innovations and their significance:
- What novel ideas, methods, or findings does this work introduce?
- Why is each contribution meaningful or impactful?
- How do they advance the field?

**🔬 Methodology**
Describe and analyze the approach taken. How do the methods work? What makes them effective or novel? Explain the key ideas behind the techniques used.

**📊 Results & Findings** (if available)
Interpret the key outcomes. What do the results tell us? How do they validate the approach? What are the implications?

**📁 Datasets & Resources** (if mentioned)
What data or resources were used? Why were they chosen?

Guidelines:
- Synthesize and interpret, don't just extract
- Explain WHY and HOW, not just WHAT
- Connect ideas across sections
- Be insightful and analytical
- Stay grounded in facts from the paper
- Use clear, engaging academic language"""

        # Retry logic - up to 2 attempts
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:  # 2 minute timeout
                    response = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": "llama3.2:3b",
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.6,  # Higher for creative, analytical synthesis
                                "top_p": 0.9,  # Nucleus sampling for better quality
                                "num_predict": 3500,  # More tokens for detailed analysis
                                "num_ctx": 8192  # Larger context window
                            }
                        }
                    )

                if response.status_code != 200:
                    logger.warning(f"Summary generation failed (attempt {attempt + 1}): {response.status_code}")
                    if attempt < 1:
                        continue
                    raise Exception(f"Ollama request failed: {response.status_code}")

                # Parse response
                ollama_response = response.json()

                # Handle response - it should be a string, but check type
                response_data = ollama_response.get('response', '')
                if isinstance(response_data, dict):
                    # If response is a dict, try to extract text
                    summary = response_data.get('text', '') or str(response_data)
                else:
                    summary = str(response_data).strip()

                if len(summary) < 100:  # If summary too short, retry
                    logger.warning(f"Summary too short (attempt {attempt + 1}), retrying...")
                    if attempt < 1:
                        continue

                logger.info(f"Successfully generated summary ({len(summary)} chars)")
                return summary

            except Exception as e:
                logger.warning(f"Summary generation attempt {attempt + 1} failed: {e}")
                if attempt < 1:
                    continue
                # Return abstract as fallback
                return f"**📋 Overview**\n\n{abstract}\n\n*Note: Detailed summary could not be generated.*"

        # Fallback
        return f"**📋 Overview**\n\n{abstract}\n\n*Note: Detailed summary could not be generated.*"

    def analyze_paper_structure(
        self,
        title: str,
        abstract: str,
        full_text: str
    ) -> Dict:
        """Extract key components from paper"""

        # Only extract from abstract if no full text
        if not full_text or len(full_text) < 500:
            structure = {
                'title': title,
                'abstract_sentences': self.split_abstract_into_key_points(abstract),
                'problem': [],
                'contributions': self.extract_contributions(abstract, ''),
                'methodology': {'steps': [], 'algorithms': [], 'models': [], 'data_processing': []},
                'techniques': [],
                'results': [],
                'datasets': []
            }
        else:
            structure = {
                'title': title,
                'abstract_sentences': self.split_abstract_into_key_points(abstract),
                'problem': self.extract_problem_statement(abstract),
                'contributions': self.extract_contributions(abstract, full_text),
                'methodology': self.extract_methodology(full_text),
                'techniques': self.extract_techniques(full_text),
                'results': self.extract_key_results(full_text),
                'datasets': self.extract_datasets(full_text)
            }

        return structure

    def split_abstract_into_key_points(self, abstract: str) -> List[str]:
        """Split abstract into key sentences"""
        if not abstract:
            return []

        # Split by sentence and filter out very short ones
        sentences = [s.strip() for s in abstract.split('.') if len(s.strip()) > 30]
        # Return first 4-5 key sentences
        return [s + '.' for s in sentences[:5]]

    def extract_problem_statement(self, abstract: str) -> List[str]:
        """Extract problem statement from abstract - returns multiple aspects"""
        if not abstract:
            return []

        problems = []
        sentences = [s.strip() + '.' for s in abstract.split('.') if len(s.strip()) > 20]

        # Look for problem indicators
        problem_patterns = [
            r'(?:problem|challenge|issue|difficulty|limitation)[s]?[:\s]+([^.]+)',
            r'(?:however|but|unfortunately|yet)[,\s]+([^.]+)',
            r'(?:lack of|absence of|need for|require[s]?)[:\s]+([^.]+)',
            r'(?:currently|existing|traditional|previous)\s+(?:methods|approaches|systems|solutions)[^\.]+((?:cannot|unable|fail|struggle)[^\.]+)',
        ]

        for pattern in problem_patterns:
            matches = re.findall(pattern, abstract, re.IGNORECASE)
            for match in matches:
                text = match if isinstance(match, str) else match[0]
                if len(text.strip()) > 15:
                    problems.append(text.strip()[:150])

        # If no explicit problems found, use first 2 sentences as context
        if not problems and sentences:
            problems = sentences[:2]

        return problems[:3]

    def extract_contributions(
        self,
        abstract: str,
        full_text: str
    ) -> List[str]:
        """Extract main contributions - only what's explicitly stated"""
        contributions = []

        # More conservative patterns - only explicit contributions
        contrib_patterns = [
            r'(?:we|this paper|this work)\s+(?:propose|present|introduce)\s+([^.,]+(?:to|for|that)[^.]+)',
            r'(?:our|the)\s+(?:main|key|primary)\s+contribution[s]?\s+(?:is|are)\s+([^.]+)',
        ]

        # Only search in abstract for accuracy
        text_to_search = abstract

        for pattern in contrib_patterns:
            matches = re.findall(pattern, text_to_search, re.IGNORECASE)
            for match in matches:
                text = match.strip()
                # Be very selective - only keep well-formed contributions
                if 30 < len(text) < 200 and text.count(' ') > 4:
                    contributions.append(text)

        # Deduplicate
        seen = set()
        unique_contributions = []
        for contrib in contributions:
            contrib_lower = contrib.lower()[:50]
            if contrib_lower not in seen:
                seen.add(contrib_lower)
                unique_contributions.append(contrib[:180])

        return unique_contributions[:3]  # Max 3 contributions

    def extract_methodology(self, full_text: str) -> Dict[str, List[str]]:
        """Extract methodology steps and components"""

        methodology = {
            'steps': [],
            'algorithms': [],
            'models': [],
            'data_processing': []
        }

        # Find methodology section
        method_section = self._extract_section(full_text, 'methodology')
        if not method_section:
            method_section = full_text[:10000]  # Use beginning of paper

        # Extract numbered steps
        step_patterns = [
            r'(?:^|\n)\s*(?:\d+\)|Step\s+\d+|First|Second|Third|Fourth|Finally)[:\s]+([^\n]+)',
            r'(?:\(\d+\))\s+([^.\n]+[.\n])'
        ]

        for pattern in step_patterns:
            matches = re.findall(pattern, method_section, re.IGNORECASE | re.MULTILINE)
            methodology['steps'].extend([m.strip() for m in matches if len(m.strip()) > 10])

        # Extract algorithms/models
        algo_pattern = r'(?:algorithm|model|network|architecture|approach)[:\s]+([A-Z][A-Za-z0-9-_ ]+)(?:\s|,|\.)'
        algorithms = re.findall(algo_pattern, method_section, re.IGNORECASE)
        methodology['algorithms'] = list(set(algorithms[:10]))

        # Extract data processing steps
        data_patterns = [
            r'(?:preprocessing|normalization|augmentation|filtering|cleaning)[:\s]+([^\n]+)',
            r'(?:training|validation|testing)[:\s]+([^\n]+)'
        ]

        for pattern in data_patterns:
            matches = re.findall(pattern, method_section, re.IGNORECASE)
            methodology['data_processing'].extend([m.strip()[:150] for m in matches])

        # Clean and deduplicate
        for key in methodology:
            methodology[key] = list(dict.fromkeys(methodology[key]))[:5]

        return methodology

    def extract_techniques(self, full_text: str) -> List[str]:
        """Extract key techniques and methods used - DISABLED for abstract-only papers"""
        # Do not extract techniques without full text to avoid false positives
        # Keywords like 'gan' can match 'organ', 'bert' can match 'robert', etc.
        return []

    def extract_key_results(self, full_text: str) -> List[str]:
        """Extract key results and findings"""

        results = []

        # Find results section
        results_section = self._extract_section(full_text, 'results')
        if not results_section:
            # Look in last part of paper
            results_section = full_text[-10000:]

        # Look for result indicators
        result_patterns = [
            r'(?:achieve|obtain|reach|demonstrate|show)s?\s+(?:a|an|the)?\s*([^.]+accuracy[^.]+\.)',
            r'(?:achieve|obtain|reach)s?\s+(?:a|an)?\s*([^.]+performance[^.]+\.)',
            r'(?:outperform|surpass|exceed|beat)s?\s+([^.]+\.)',
            r'(?:improvement|increase|boost)\s+of\s+([^.]+\.)',
            r'(?:accuracy|precision|recall|f1-score|auc)[:\s]+([0-9.]+%?)'
        ]

        for pattern in result_patterns:
            matches = re.findall(pattern, results_section, re.IGNORECASE)
            results.extend([m.strip()[:150] for m in matches if len(str(m).strip()) > 5])

        return list(dict.fromkeys(results))[:5]

    def extract_datasets(self, full_text: str) -> List[str]:
        """Extract datasets used"""

        datasets = []

        # Common dataset patterns
        dataset_patterns = [
            r'(?:dataset|corpus|benchmark)[:\s]+([A-Z][A-Za-z0-9-]+)',
            r'(?:MNIST|CIFAR|ImageNet|COCO|Pascal VOC|SQuAD|GLUE|WikiText)',
            r'(?:we use|we utilize|we employ)\s+the\s+([A-Z][A-Za-z0-9-]+)\s+dataset'
        ]

        for pattern in dataset_patterns:
            matches = re.findall(pattern, full_text[:10000], re.IGNORECASE)
            datasets.extend(matches)

        return list(set(datasets))[:5]

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a specific section from paper text"""

        if section_name not in self.section_patterns:
            return ""

        pattern = self.section_patterns[section_name]
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)

        if match:
            start = match.end()
            # Find next section or take 5000 chars
            next_section = re.search(r'\n\s*\d+\.\s+[A-Z]', text[start:start+10000])
            end = start + (next_section.start() if next_section else 5000)
            return text[start:end]

        return ""

    def _build_mindmap_tree(
        self,
        structure: Dict,
        include_methodology: bool,
        include_results: bool,
        include_contributions: bool,
        max_depth: int
    ) -> Dict:
        """Build hierarchical mind-map tree"""

        def to_string(value):
            """Safely convert any value to string"""
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                # For dicts, try to get a 'text' or 'content' field, or convert to JSON
                return value.get('text', value.get('content', str(value)))
            elif isinstance(value, list):
                return ' '.join(to_string(v) for v in value)
            else:
                return str(value)

        root = {
            'id': 'root',
            'label': to_string(structure['title'])[:100],
            'type': 'root',
            'children': []
        }

        # If we only have abstract, show key points from it
        if structure.get('abstract_sentences') and not structure.get('problem'):
            abstract_node = {
                'id': 'abstract',
                'label': 'Key Points',
                'type': 'section',
                'children': []
            }
            for i, sentence in enumerate(structure['abstract_sentences'][:6]):  # Increased from 4
                sentence_str = to_string(sentence)
                if sentence_str and len(sentence_str.strip()) > 20:
                    abstract_node['children'].append({
                        'id': f'point_{i}',
                        'label': sentence_str[:200],  # Increased from 150
                        'type': 'item',
                        'children': []
                    })
            if abstract_node['children']:
                root['children'].append(abstract_node)
        # Otherwise show problem statement from full analysis
        elif structure['problem']:
            problem_node = {
                'id': 'problem',
                'label': 'Problem & Motivation',
                'type': 'section',
                'children': []
            }
            problems = structure['problem'] if isinstance(structure['problem'], list) else [structure['problem']]
            for i, prob in enumerate(problems[:5]):  # Increased from 3
                prob_str = to_string(prob)
                if prob_str and len(prob_str.strip()) > 10:
                    problem_node['children'].append({
                        'id': f'problem_{i}',
                        'label': prob_str[:180],  # Increased from 120
                        'type': 'item',
                        'children': []
                    })
            if problem_node['children']:
                root['children'].append(problem_node)

        # Contributions branch
        if include_contributions and structure['contributions']:
            contrib_node = {
                'id': 'contributions',
                'label': 'Key Contributions',
                'type': 'section',
                'children': []
            }
            for i, contrib in enumerate(structure['contributions'][:7]):  # Increased from 3
                contrib_str = to_string(contrib)
                contrib_node['children'].append({
                    'id': f'contrib_{i}',
                    'label': contrib_str[:150],  # Increased from 80
                    'type': 'item',
                    'children': []
                })
            root['children'].append(contrib_node)

        # Methodology branch
        if include_methodology:
            method_node = {
                'id': 'methodology',
                'label': 'Methodology',
                'type': 'section',
                'children': []
            }

            # Add steps
            if structure['methodology']['steps']:
                steps_node = {
                    'id': 'method_steps',
                    'label': 'Approach Steps',
                    'type': 'subsection',
                    'children': []
                }
                for i, step in enumerate(structure['methodology']['steps'][:6]):  # Increased from 4
                    step_str = to_string(step)
                    steps_node['children'].append({
                        'id': f'step_{i}',
                        'label': f"{i+1}. {step_str[:120]}",  # Increased from 70
                        'type': 'item',
                        'children': []
                    })
                method_node['children'].append(steps_node)

            # Add techniques
            if structure['techniques']:
                tech_node = {
                    'id': 'techniques',
                    'label': 'Key Techniques',
                    'type': 'subsection',
                    'children': []
                }
                for i, tech in enumerate(structure['techniques'][:8]):  # Increased from 6
                    tech_str = to_string(tech)
                    tech_node['children'].append({
                        'id': f'tech_{i}',
                        'label': tech_str[:100],  # Added length limit
                        'type': 'technique',
                        'children': []
                    })
                method_node['children'].append(tech_node)

            root['children'].append(method_node)

        # Results branch
        if include_results and structure['results']:
            results_node = {
                'id': 'results',
                'label': 'Results & Findings',
                'type': 'section',
                'children': []
            }
            for i, result in enumerate(structure['results'][:6]):  # Increased from 4
                result_str = to_string(result)
                results_node['children'].append({
                    'id': f'result_{i}',
                    'label': result_str[:150],  # Increased from 80
                    'type': 'result',
                    'children': []
                })
            root['children'].append(results_node)

        # Datasets branch
        if structure['datasets']:
            data_node = {
                'id': 'datasets',
                'label': 'Datasets',
                'type': 'section',
                'children': []
            }
            for i, dataset in enumerate(structure['datasets']):
                dataset_str = to_string(dataset)
                data_node['children'].append({
                    'id': f'dataset_{i}',
                    'label': dataset_str,
                    'type': 'item',
                    'children': []
                })
            root['children'].append(data_node)

        return root

    def _generate_graphviz_svg(self, title: str, root_node: Dict) -> str:
        """Generate SVG using Graphviz"""

        dot = graphviz.Digraph(comment=title)
        dot.attr(rankdir='TB', size='12,12', dpi='300')
        dot.attr('node', fontname='Arial', fontsize='10')
        dot.attr('edge', color='gray60')

        # Style mappings
        node_styles = {
            'root': {'shape': 'box', 'style': 'filled,rounded', 'fillcolor': '#4A90E2', 'fontcolor': 'white', 'fontsize': '14'},
            'section': {'shape': 'box', 'style': 'filled,rounded', 'fillcolor': '#7ED321', 'fontcolor': 'white', 'fontsize': '12'},
            'subsection': {'shape': 'box', 'style': 'filled,rounded', 'fillcolor': '#F5A623', 'fontcolor': 'white'},
            'item': {'shape': 'box', 'style': 'filled', 'fillcolor': '#E8F4F8'},
            'technique': {'shape': 'ellipse', 'style': 'filled', 'fillcolor': '#FFE8B6'},
            'result': {'shape': 'box', 'style': 'filled', 'fillcolor': '#D4F4DD'}
        }

        def add_node_recursive(node: Dict, parent_id: Optional[str] = None):
            """Recursively add nodes to graph"""
            node_id = node['id']
            label = node['label']
            node_type = node['type']

            # Wrap long labels
            if len(label) > 50:
                words = label.split()
                lines = []
                current_line = []
                current_length = 0
                for word in words:
                    if current_length + len(word) > 40:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                        current_length = len(word)
                    else:
                        current_line.append(word)
                        current_length += len(word) + 1
                if current_line:
                    lines.append(' '.join(current_line))
                label = '\\n'.join(lines[:3])  # Max 3 lines

            # Add node
            style = node_styles.get(node_type, {})
            dot.node(node_id, label, **style)

            # Add edge from parent
            if parent_id:
                dot.edge(parent_id, node_id)

            # Recursively add children
            for child in node.get('children', []):
                add_node_recursive(child, node_id)

        add_node_recursive(root_node)

        # Render to SVG string
        try:
            svg_data = dot.pipe(format='svg').decode('utf-8')
            return svg_data
        except Exception as e:
            logger.error(f"Error generating SVG: {e}")
            return ""
