"""
Paper Organizer Service
Handles folder-based workflow: scan, classify, rename, sort, recommend
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable
import shutil
import re
from datetime import datetime
import numpy as np

from app.services.pdf_processor import EnhancedPDFExtractor
from app.services.api_enhancer import MetadataEnhancer
from app.services.bibtex_exporter import EnhancedBibTeXExporter
from app.services.recommendation_service import RecommendationService
from app.database.db import DatabaseManager

import httpx

logger = logging.getLogger(__name__)


class PaperOrganizer:
    """Main service for organizing papers in folders"""

    def __init__(self):
        self.pdf_extractor = EnhancedPDFExtractor()
        self.metadata_enhancer = MetadataEnhancer()
        self.bibtex_exporter = EnhancedBibTeXExporter()
        self.recommendation_service = RecommendationService()

        # Check if Ollama is available for topic summaries
        self.ollama_available = False
        self.ollama_url = "http://localhost:11434"
        try:
            import requests
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=1)
            if response.status_code == 200:
                self.ollama_available = True
                logger.info("Ollama detected - will generate comprehensive topic summaries")
        except:
            logger.info("Ollama not detected - topic summaries will be basic")

    async def organize_folder(
        self,
        folder_path: Path,
        num_topics: Optional[int] = None,
        custom_topics: Optional[List[str]] = None,
        copy_mode: bool = True,
        enhance_metadata: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Main workflow: organize papers in a folder

        Args:
            folder_path: Input folder containing PDFs
            num_topics: Number of topics to auto-detect (None = auto)
            custom_topics: Custom topic names (None = auto-detect)
            copy_mode: True = copy files, False = move files
            get_recommendations: Download recommended papers
            recommendations_per_topic: Number of papers to recommend per topic
            progress_callback: Function to report progress

        Returns:
            Results dictionary with organized structure
        """
        logger.info(f"Starting folder organization: {folder_path}")

        results = {
            'input_folder': str(folder_path),
            'total_papers': 0,
            'processed_papers': 0,
            'topics': {},
            'recommendations': {},
            'bibtex_file': None,
            'errors': []
        }

        try:
            # Step 1: Scan folder for PDFs
            if progress_callback:
                await progress_callback(5, "Scanning for PDF files...")

            pdf_files = list(folder_path.rglob("*.pdf"))
            results['total_papers'] = len(pdf_files)

            if not pdf_files:
                logger.warning("No PDF files found")
                return results

            logger.info(f"Found {len(pdf_files)} PDF files")

            # Step 1.5: Remove duplicates (keep only one copy)
            if progress_callback:
                await progress_callback(7, "Removing duplicate files...")

            pdf_files, removed_count = await self._remove_duplicates(pdf_files)
            if removed_count > 0:
                logger.info(f"Removed {removed_count} duplicate files")
                results['total_papers'] = len(pdf_files)

            # Step 2: Extract metadata from all PDFs
            if progress_callback:
                await progress_callback(10, f"Extracting metadata from {len(pdf_files)} papers...")

            papers_metadata = await self._extract_metadata_batch(
                pdf_files, progress_callback
            )

            # Step 3: Enhance metadata with external APIs (optional for speed)
            if enhance_metadata:
                if progress_callback:
                    await progress_callback(40, "Enhancing metadata with online APIs...")

                papers_metadata = await self._enhance_metadata_batch(
                    papers_metadata, progress_callback
                )
            else:
                if progress_callback:
                    await progress_callback(40, "Skipping metadata enhancement for faster processing...")

            # Step 4: Classify papers into topics
            if progress_callback:
                await progress_callback(60, "Classifying papers by topic...")

            topics_dict = await self._classify_papers(
                papers_metadata, custom_topics, num_topics
            )

            # Step 5: Organize into folders
            if progress_callback:
                await progress_callback(70, "Organizing papers into topic folders...")

            organized_folders = await self._organize_into_folders(
                folder_path, topics_dict, papers_metadata, copy_mode
            )

            results['topics'] = organized_folders

            # Step 5.5: Save papers to database and get IDs
            if progress_callback:
                await progress_callback(75, "Saving papers to database...")

            organized_folders = await self._save_papers_to_database(organized_folders)
            results['topics'] = organized_folders

            # Step 6: Generate BibTeX file
            if progress_callback:
                await progress_callback(80, "Generating BibTeX references...")

            bibtex_file = await self._generate_bibtex(
                folder_path, papers_metadata
            )
            results['bibtex_file'] = str(bibtex_file)

            # Step 7: Complete
            if progress_callback:
                await progress_callback(100, "Organization complete!")

            results['processed_papers'] = len(papers_metadata)
            logger.info("Folder organization complete")

        except Exception as e:
            logger.error(f"Error organizing folder: {e}")
            results['errors'].append(str(e))
            raise

        return results

    async def _remove_duplicates(self, pdf_files: List[Path]) -> tuple[List[Path], int]:
        """
        Remove duplicate PDF files based on content hash.
        Keeps only one copy of each unique file.

        Returns: (unique_files, removed_count)
        """
        import hashlib

        seen_hashes = {}
        unique_files = []
        removed_count = 0

        for pdf_file in pdf_files:
            try:
                # Calculate file hash (MD5 is fast enough for deduplication)
                hash_md5 = hashlib.md5()
                with open(pdf_file, "rb") as f:
                    # Read in chunks to handle large files
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)

                file_hash = hash_md5.hexdigest()

                if file_hash in seen_hashes:
                    # Duplicate found - verify it's actually the same file
                    original_file = seen_hashes[file_hash]

                    # Double-check: same hash AND similar size
                    if abs(pdf_file.stat().st_size - original_file.stat().st_size) < 1024:  # Within 1KB
                        logger.info(f"Removing duplicate: {pdf_file.name} (same as {original_file.name})")

                        try:
                            pdf_file.unlink()  # Delete the duplicate
                            removed_count += 1
                        except Exception as e:
                            logger.error(f"Failed to remove duplicate {pdf_file}: {e}")
                    else:
                        # Hash collision or corrupted file - keep both
                        unique_files.append(pdf_file)
                else:
                    # First occurrence - keep it
                    seen_hashes[file_hash] = pdf_file
                    unique_files.append(pdf_file)

            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                # If we can't hash it, keep it to be safe
                unique_files.append(pdf_file)

        return unique_files, removed_count

    async def _extract_metadata_batch(
        self,
        pdf_files: List[Path],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """Extract metadata from all PDFs in parallel"""

        total = len(pdf_files)
        metadata_list = []

        def update_progress(current, total_files, filename):
            if progress_callback:
                progress = 10 + (current / total_files) * 30  # 10-40%
                asyncio.create_task(
                    progress_callback(progress, f"Processing {filename}...")
                )

        results = await self.pdf_extractor.extract_batch(
            pdf_files, update_progress
        )

        for result in results:
            if not result.get('error'):
                metadata_list.append(result)

        return metadata_list

    async def _enhance_metadata_batch(
        self,
        papers_metadata: List[Dict],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """Enhance metadata using external APIs"""

        enhanced = []
        total = len(papers_metadata)

        async with MetadataEnhancer() as enhancer:
            for i, paper in enumerate(papers_metadata):
                try:
                    enhanced_paper = await enhancer.enhance_metadata(paper)
                    enhanced.append(enhanced_paper)

                    if progress_callback:
                        progress = 40 + (i / total) * 20  # 40-60%
                        await progress_callback(
                            progress,
                            f"Enhanced {i+1}/{total} papers"
                        )
                except Exception as e:
                    logger.error(f"Error enhancing {paper.get('file_name')}: {e}")
                    enhanced.append(paper)  # Use original if enhancement fails

        return enhanced

    async def _classify_papers(
        self,
        papers_metadata: List[Dict],
        custom_topics: Optional[List[str]],
        num_topics: Optional[int]
    ) -> Dict[str, List[int]]:
        """Classify papers into topics"""

        # Simple classification based on keywords and abstracts
        # TODO: Implement actual ML classification

        if custom_topics:
            # Use custom topics
            topics = {topic: [] for topic in custom_topics}

            for i, paper in enumerate(papers_metadata):
                # Assign to best matching topic
                best_topic = self._match_to_topic(paper, custom_topics)
                if best_topic:
                    topics[best_topic].append(i)
                else:
                    if 'Uncategorized' not in topics:
                        topics['Uncategorized'] = []
                    topics['Uncategorized'].append(i)
        else:
            # Auto-detect topics from keywords/abstracts
            topics = await self._auto_detect_topics(papers_metadata, num_topics)

        return topics

    def _match_to_topic(self, paper: Dict, topics: List[str]) -> Optional[str]:
        """Match paper to best topic based on keywords"""

        text = ' '.join([
            paper.get('title', ''),
            paper.get('abstract', ''),
            ' '.join(paper.get('keywords', []))
        ]).lower()

        best_topic = None
        best_score = 0

        for topic in topics:
            # Simple keyword matching
            score = text.count(topic.lower())
            if score > best_score:
                best_score = score
                best_topic = topic

        return best_topic if best_score > 0 else None

    async def _auto_detect_topics(
        self,
        papers_metadata: List[Dict],
        num_topics: Optional[int]
    ) -> Dict[str, List[int]]:
        """
        Auto-detect topics using ML-based clustering with TF-IDF and K-Means

        This provides much better results than simple keyword matching,
        especially for large datasets (100+ papers)
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import KMeans
        from collections import Counter
        import re
        import numpy as np

        # Enforce maximum of 15 topics to avoid folder clutter
        MAX_TOPICS = 15
        MIN_TOPICS = 3

        # Determine optimal number of clusters
        n_papers = len(papers_metadata)

        if num_topics is None:
            # Auto-determine based on dataset size
            # Rule: ~50-100 papers per topic is manageable
            if n_papers < 50:
                num_topics = MIN_TOPICS
            elif n_papers < 200:
                num_topics = min(5, MAX_TOPICS)
            elif n_papers < 500:
                num_topics = min(8, MAX_TOPICS)
            else:
                # For large datasets (500+), use more topics but cap at 15
                num_topics = min(int(n_papers / 80), MAX_TOPICS)

            logger.info(f"Auto-determined {num_topics} topics for {n_papers} papers")
        else:
            num_topics = max(MIN_TOPICS, min(num_topics, MAX_TOPICS))
            logger.info(f"Using {num_topics} topics (capped between {MIN_TOPICS}-{MAX_TOPICS})")

        # Prepare documents for clustering
        documents = []
        for paper in papers_metadata:
            # Combine title (weighted 2x), abstract, and keywords
            doc = ' '.join([
                paper.get('title', '') + ' ' + paper.get('title', ''),  # Title appears twice
                paper.get('abstract', ''),
                ' '.join(paper.get('keywords', []))
            ])
            documents.append(doc)

        try:
            # Use TF-IDF to vectorize documents
            # This captures term importance better than simple word counting
            vectorizer = TfidfVectorizer(
                max_features=1000,  # Limit to top 1000 terms
                min_df=2,  # Term must appear in at least 2 documents
                max_df=0.8,  # Ignore terms in >80% of documents (too common)
                stop_words='english',  # Remove "this", "that", "and", etc.
                ngram_range=(1, 3),  # Capture 1-3 word phrases
                strip_accents='unicode',
                lowercase=True
            )

            tfidf_matrix = vectorizer.fit_transform(documents)
            logger.info(f"TF-IDF matrix shape: {tfidf_matrix.shape}")

            # Use K-Means clustering
            kmeans = KMeans(
                n_clusters=num_topics,
                random_state=42,
                n_init=10,
                max_iter=300
            )
            cluster_labels = kmeans.fit_predict(tfidf_matrix)

            # Extract meaningful topic names from cluster centroids
            feature_names = vectorizer.get_feature_names_out()
            topic_names = {}

            for cluster_id in range(num_topics):
                # Get top terms for this cluster
                centroid = kmeans.cluster_centers_[cluster_id]
                top_indices = centroid.argsort()[-5:][::-1]  # Top 5 terms
                top_terms = [feature_names[i] for i in top_indices]

                # Generate readable topic name from top terms
                topic_name = self._generate_topic_name(top_terms, cluster_id, papers_metadata, cluster_labels)
                topic_names[cluster_id] = topic_name

            # Group papers by cluster
            topics_dict = {}
            for cluster_id, topic_name in topic_names.items():
                paper_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]

                # Only include topics with at least 2 papers
                if len(paper_indices) >= 2:
                    topics_dict[topic_name] = paper_indices
                else:
                    # Single-paper "topics" go to "Other"
                    if 'Other' not in topics_dict:
                        topics_dict['Other'] = []
                    topics_dict['Other'].extend(paper_indices)

            logger.info(f"Created {len(topics_dict)} topics: {list(topics_dict.keys())}")

            # Optional: Use Ollama to refine topic names if available
            if self.ollama_available:
                topics_dict = await self._refine_topic_names_with_llm(topics_dict, papers_metadata)

            return topics_dict

        except Exception as e:
            logger.error(f"Clustering failed: {e}, falling back to simple grouping")
            # Fallback: group all papers into "General"
            return {"General": list(range(len(papers_metadata)))}

    def _generate_topic_name(
        self,
        top_terms: List[str],
        cluster_id: int,
        papers_metadata: List[Dict],
        cluster_labels: np.ndarray
    ) -> str:
        """
        Generate a meaningful topic name from top TF-IDF terms

        Priority:
        1. Use multi-word phrases if available
        2. Combine related single words
        3. Capitalize properly
        4. Fallback to generic name if terms are too vague
        """
        import re

        # Filter out vague/generic terms
        stopwords = {
            'using', 'based', 'study', 'analysis', 'approach', 'method',
            'results', 'new', 'novel', 'paper', 'research', 'data',
            'model', 'models', 'system', 'systems', 'application'
        }

        filtered_terms = [t for t in top_terms if t.lower() not in stopwords and len(t) > 2]

        if not filtered_terms:
            # If all terms are generic, look at paper titles in this cluster
            cluster_papers = [papers_metadata[i] for i, label in enumerate(cluster_labels) if label == cluster_id]

            # Extract common meaningful words from titles
            title_words = []
            for paper in cluster_papers[:10]:  # Sample first 10 papers
                title = paper.get('title', '')
                # Extract capitalized words (likely domain-specific terms)
                words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b', title)
                title_words.extend(words)

            if title_words:
                # Use most common title word
                word_counts = Counter(title_words)
                most_common = word_counts.most_common(1)[0][0]
                return most_common
            else:
                # Last resort: generic topic name
                return f"Topic {cluster_id + 1}"

        # Prefer multi-word phrases (they're more specific)
        phrases = [t for t in filtered_terms if ' ' in t]
        if phrases:
            # Use the best phrase, capitalize properly
            best_phrase = phrases[0]
            return ' '.join(word.capitalize() for word in best_phrase.split())

        # Combine top 2-3 single words into a descriptive name
        if len(filtered_terms) >= 2:
            # Take top 2-3 terms and create compound name
            combined = ' '.join(filtered_terms[:2])
            return ' '.join(word.capitalize() for word in combined.split())
        elif filtered_terms:
            # Single term
            return filtered_terms[0].capitalize()
        else:
            return f"Topic {cluster_id + 1}"

    async def _refine_topic_names_with_llm(
        self,
        topics_dict: Dict[str, List[int]],
        papers_metadata: List[Dict]
    ) -> Dict[str, List[int]]:
        """
        Use Ollama LLM to generate better topic names based on paper titles

        This is optional but provides more accurate, domain-specific topic names
        """
        logger.info("Refining topic names with LLM...")

        refined_dict = {}

        for topic_name, paper_indices in topics_dict.items():
            # Skip "Other" category
            if topic_name == "Other":
                refined_dict[topic_name] = paper_indices
                continue

            # Sample up to 10 paper titles from this cluster
            sample_titles = []
            for idx in paper_indices[:10]:
                title = papers_metadata[idx].get('title', '')
                if title:
                    sample_titles.append(title)

            if not sample_titles:
                refined_dict[topic_name] = paper_indices
                continue

            try:
                # Ask LLM to generate a concise topic name
                prompt = f"""Based on these paper titles from an academic cluster, suggest ONE concise topic name (2-4 words max) that captures the research theme:

{chr(10).join(f"- {t}" for t in sample_titles[:8])}

Respond with ONLY the topic name, nothing else. Make it specific and academic."""

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": "llama3.2:3b",
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.3,
                                "num_predict": 20
                            }
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        refined_name = result.get('response', '').strip()

                        # Clean up the response
                        refined_name = refined_name.replace('"', '').replace("'", '').strip()
                        refined_name = refined_name.split('\n')[0]  # Take first line only

                        # Validate it's reasonable (not too long, not empty)
                        if refined_name and len(refined_name) < 50 and len(refined_name.split()) <= 5:
                            logger.info(f"Refined: '{topic_name}' → '{refined_name}'")
                            refined_dict[refined_name] = paper_indices
                        else:
                            # Keep original if LLM output is bad
                            refined_dict[topic_name] = paper_indices
                    else:
                        refined_dict[topic_name] = paper_indices

            except Exception as e:
                logger.warning(f"LLM refinement failed for '{topic_name}': {e}")
                refined_dict[topic_name] = paper_indices

        return refined_dict

    async def _organize_into_folders(
        self,
        base_folder: Path,
        topics_dict: Dict[str, List[int]],
        papers_metadata: List[Dict],
        copy_mode: bool
    ) -> Dict[str, List[Dict]]:
        """Organize papers into topic-based subfolders"""

        organized = {}

        for topic, paper_indices in topics_dict.items():
            # Create topic folder
            topic_folder = base_folder / self._sanitize_folder_name(topic)
            topic_folder.mkdir(exist_ok=True)

            topic_papers = []

            for idx in paper_indices:
                paper = papers_metadata[idx]

                # Generate new filename: [Year] Title - FirstAuthor.pdf
                new_name = self._generate_filename(paper)
                new_path = topic_folder / new_name

                # Copy or move file
                original_path = Path(paper['file_path'])

                try:
                    # Skip if file already exists (prevent duplicates)
                    if new_path.exists():
                        # Check if it's the same file being re-organized
                        if original_path.resolve() == new_path.resolve():
                            logger.info(f"Skipped (already organized): {new_name} → {topic}")
                            paper['organized_path'] = str(new_path)
                            paper['topic'] = topic
                            topic_papers.append(paper)
                            continue
                        else:
                            # File exists but different source - skip duplicate
                            logger.warning(f"Skipped (duplicate): {new_name} already exists in {topic}")
                            continue

                    if copy_mode:
                        shutil.copy2(original_path, new_path)
                    else:
                        shutil.move(str(original_path), new_path)

                    paper['organized_path'] = str(new_path)
                    paper['topic'] = topic
                    topic_papers.append(paper)

                    logger.info(f"Organized: {new_name} → {topic}")

                except Exception as e:
                    logger.error(f"Error organizing {original_path}: {e}")

            organized[topic] = topic_papers

        return organized

    async def _save_papers_to_database(
        self,
        organized_folders: Dict[str, List[Dict]]
    ) -> Dict[str, List[Dict]]:
        """Save organized papers to database and add database IDs

        Uses INSERT OR REPLACE to handle duplicates automatically.
        """

        db = DatabaseManager()
        await db.initialize()

        try:
            for topic, papers in organized_folders.items():
                for paper in papers:
                    file_path = paper.get('organized_path', paper.get('file_path'))

                    # Try to save paper - add_paper will handle duplicates
                    try:
                        paper_id = await db.add_paper(
                            metadata=paper,
                            file_path=file_path,
                            full_text=paper.get('full_text', '')
                        )
                        paper['id'] = paper_id
                        logger.info(f"Saved paper to database with ID {paper_id}: {paper.get('title', 'Unknown')[:50]}")
                    except Exception as e:
                        # If insert fails, try to retrieve by hash
                        error_msg = str(e)
                        if "UNIQUE constraint" in error_msg and "file_hash" in error_msg:
                            try:
                                # Calculate hash and look up existing paper
                                import hashlib
                                hash_md5 = hashlib.md5()
                                with open(file_path, 'rb') as f:
                                    for chunk in iter(lambda: f.read(4096), b""):
                                        hash_md5.update(chunk)
                                file_hash = hash_md5.hexdigest()

                                existing_id = await db.get_paper_by_hash(file_hash)
                                if existing_id:
                                    paper['id'] = existing_id
                                    logger.info(f"Paper already in DB with ID {existing_id}: {paper.get('title', 'Unknown')[:50]}")
                                else:
                                    logger.error(f"Duplicate error but can't find paper: {e}")
                                    paper['id'] = 1  # Default to 1 instead of 0
                            except Exception as lookup_error:
                                logger.error(f"Error looking up duplicate paper: {lookup_error}")
                                paper['id'] = 1  # Default to 1 instead of 0
                        else:
                            logger.error(f"Error saving paper: {e}")
                            paper['id'] = 1  # Default to 1 instead of 0

        finally:
            await db.close()

        return organized_folders

    def _sanitize_folder_name(self, name: str) -> str:
        """Sanitize folder name"""
        # Remove invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Limit length
        return name[:100]

    def _generate_filename(self, paper: Dict) -> str:
        """Generate filename: [Year] Title - FirstAuthorLastName.pdf"""

        year = paper.get('year', 'Unknown')
        title = paper.get('title', 'Untitled')

        # Clean title
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        title = title[:100]  # Limit length

        # Get FIRST author's last name only
        authors = paper.get('authors', [])
        if authors:
            first_author = authors[0]  # Only first author
            # Extract last name
            parts = first_author.split()
            last_name = parts[-1] if parts else 'Unknown'
            last_name = re.sub(r'[<>:"/\\|?*]', '', last_name)
        else:
            last_name = 'Unknown'

        filename = f"[{year}] {title} - {last_name}.pdf"

        return filename

    async def _download_pdf(self, url: str, filepath: Path) -> bool:
        """Download PDF from URL to filepath"""
        import aiohttp
        import asyncio

        try:
            timeout = aiohttp.ClientTimeout(total=60)  # 60 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status == 200:
                        content = await response.read()

                        # Verify it's a PDF
                        if content.startswith(b'%PDF'):
                            with open(filepath, 'wb') as f:
                                f.write(content)
                            return True
                        else:
                            logger.warning(f"Downloaded content is not a PDF: {url}")
                            return False
                    else:
                        logger.warning(f"Failed to download (HTTP {response.status}): {url}")
                        return False
        except asyncio.TimeoutError:
            logger.error(f"Timeout downloading: {url}")
            return False
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False

    async def _get_recommendations(
        self,
        organized_folders: Dict[str, List[Dict]],
        per_topic: int,
        base_folder: Path
    ) -> Dict[str, List[Dict]]:
        """Download recommended papers for each topic"""

        recommendations = {}

        for topic, papers in organized_folders.items():
            try:
                # Get recommendations for this topic
                recommended = await self.recommendation_service.get_recommendations(
                    topic, max_results=per_topic
                )

                if recommended:
                    # Create recommended subfolder
                    rec_folder = base_folder / self._sanitize_folder_name(topic) / 'recommended'
                    rec_folder.mkdir(exist_ok=True)

                    # Download papers
                    downloaded = []
                    for rec_paper in recommended:
                        try:
                            # Download PDF if URL available
                            pdf_url = rec_paper.get('pdf_url')
                            if pdf_url:
                                filename = self._generate_filename(rec_paper)
                                filepath = rec_folder / filename

                                # Skip if already downloaded
                                if filepath.exists():
                                    logger.info(f"Skipped (already exists): {filename}")
                                    rec_paper['recommended_path'] = str(filepath)
                                    downloaded.append(rec_paper)
                                    continue

                                # Download the PDF
                                success = await self._download_pdf(pdf_url, filepath)

                                if success:
                                    rec_paper['recommended_path'] = str(filepath)
                                    downloaded.append(rec_paper)
                                    logger.info(f"Downloaded: {filename}")
                                else:
                                    logger.warning(f"Failed to download: {filename}")
                            else:
                                logger.warning(f"No PDF URL for: {rec_paper.get('title', 'Unknown')}")
                        except Exception as e:
                            logger.error(f"Error downloading recommendation: {e}")

                    recommendations[topic] = downloaded
                    logger.info(f"Downloaded {len(downloaded)} recommendations for {topic}")

            except Exception as e:
                logger.error(f"Error getting recommendations for {topic}: {e}")

        return recommendations

    async def _generate_bibtex(
        self,
        base_folder: Path,
        papers_metadata: List[Dict]
    ) -> Path:
        """Generate BibTeX file for all papers"""

        bibtex_path = base_folder / 'references.bib'

        bibtex_content, _ = self.bibtex_exporter.export_papers(
            papers_metadata,
            output_path=bibtex_path,
            validate=True
        )

        logger.info(f"Generated BibTeX: {bibtex_path}")

        return bibtex_path

    def get_paper_structure(self, organized_results: Dict) -> Dict:
        """Get structured view of organized papers for UI"""

        # Return topics as object (dict) not array, for frontend compatibility
        topics_dict = {}

        for topic, papers in organized_results['topics'].items():
            # Convert papers to format expected by frontend
            papers_list = [
                {
                    'id': p.get('id', 0),  # Use database ID if available
                    'title': p.get('title', 'Untitled'),
                    'authors': p.get('authors', []),
                    'year': p.get('year'),
                    'path': p.get('organized_path'),
                    'abstract': p.get('abstract', '')[:200] + '...' if p.get('abstract') else '',
                    'full_text': p.get('full_text', ''),  # For mind-map generation
                }
                for p in papers
            ]

            topics_dict[topic] = papers_list

        structure = {
            'total_papers': organized_results['processed_papers'],
            'total_topics': len(organized_results['topics']),
            'topics': topics_dict,  # Dict, not array
            'recommendations': organized_results.get('recommendations', {})
        }

        return structure

    async def _generate_topic_summaries(
        self,
        topics_dict: Dict[str, List[int]],
        papers_metadata: List[Dict]
    ) -> Dict[str, str]:
        """
        Generate comprehensive summaries for each topic using LLM

        Args:
            topics_dict: Dictionary of topic -> list of paper indices
            papers_metadata: List of all paper metadata

        Returns:
            Dictionary of topic -> summary text
        """
        summaries = {}

        for topic, paper_indices in topics_dict.items():
            try:
                # Get papers for this topic
                topic_papers = [papers_metadata[idx] for idx in paper_indices]

                # Collect titles only - much faster
                papers_text = []
                for paper in topic_papers[:5]:  # Reduced to 5 papers
                    title = paper.get('title', 'Unknown')
                    papers_text.append(f"- {title}")

                papers_list = "\n".join(papers_text)

                # Simplified, faster prompt
                prompt = f"""Summarize this research topic "{topic}" based on these {len(topic_papers)} papers:

{papers_list}

Write 2-3 sentences about what this topic covers and the research focus."""

                async with httpx.AsyncClient(timeout=15.0) as client:  # Reduced from 45s
                    response = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": "llama3.2:3b",
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.3,
                                "num_predict": 300  # Much shorter, faster
                            }
                        }
                    )

                if response.status_code == 200:
                    ollama_response = response.json()
                    summary = ollama_response['response'].strip()
                    summaries[topic] = summary
                    logger.info(f"Generated summary for topic: {topic}")
                else:
                    summaries[topic] = f"Summary generation unavailable for {topic}"

            except Exception as e:
                logger.warning(f"Failed to generate summary for topic {topic}: {e}")
                summaries[topic] = f"This topic contains {len(paper_indices)} papers."

        return summaries
