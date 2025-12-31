"""
Chunking Strategies Performance Benchmark

Comprehensive benchmarking of all chunking strategies with:
- Multiple document sizes and types
- Performance metrics (time, memory, chunk statistics)
- Visualization plots
- Standard benchmark comparisons
"""

import asyncio
import sys
import time
import tracemalloc
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics

sys.path.insert(0, '.')

from docex.processors.chunking import (
    ChunkingFactory,
    ChunkingConfig,
    FixedSizeChunking,
    RecursiveChunking,
    DocumentBasedChunking,
    SemanticChunking,
    HierarchicalChunking,
)

# Try to import matplotlib, install if needed
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import numpy as np
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False
    print("Warning: matplotlib not available. Install with: pip install matplotlib numpy")
    print("Plots will be skipped, but benchmark data will still be collected.")


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run"""
    strategy: str
    document_name: str
    document_size: int  # characters
    chunks_created: int
    avg_chunk_size: float
    min_chunk_size: int
    max_chunk_size: int
    processing_time: float  # seconds
    memory_peak: float  # MB
    memory_current: float  # MB
    chunks_per_second: float
    chars_per_second: float
    chunk_size_stddev: float
    chunk_size_median: float


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results"""
    results: List[BenchmarkResult]
    config: Dict[str, Any]
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'config': self.config,
            'results': [asdict(r) for r in self.results]
        }
    
    def save_json(self, path: str):
        """Save results to JSON file"""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_json(cls, path: str):
        """Load results from JSON file"""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(
            results=[BenchmarkResult(**r) for r in data['results']],
            config=data['config']
        )


# Standard benchmark documents
BENCHMARK_DOCUMENTS = {
    'tiny': """Short text for quick tests.""",
    
    'small': """
This is a small document for testing chunking strategies.
It contains a few paragraphs with some basic structure.
We can use this to measure baseline performance.
The document has multiple sentences and some formatting.
""",
    
    'medium': """
# Technical Documentation

## Introduction
This is a medium-sized technical document designed to test chunking strategies
on structured content. It contains multiple sections with headers and subsections.

## Features
The document includes various features:
- Bullet points
- Code examples
- Multiple paragraphs
- Hierarchical structure

### Code Example
Here's a code example:
```python
def example_function():
    return "Hello, World!"
```

## Conclusion
This concludes the medium document test.
""",
    
    'large': """
# Comprehensive Research Paper on Artificial Intelligence

## Abstract
Artificial intelligence has transformed numerous industries and continues to evolve at a rapid pace.
This paper examines the current state of AI, its applications, and future directions.

## Introduction
The field of artificial intelligence has undergone remarkable transformations over the past decade.
Deep learning, in particular, has revolutionized how machines process and understand data.
Early neural networks were limited by computational power and data availability.
However, the advent of powerful GPUs and massive datasets changed everything.
Researchers could now train models with billions of parameters, achieving unprecedented accuracy.

## Background
### Historical Context
The history of artificial intelligence dates back to the 1950s when researchers first began
exploring the possibility of creating machines that could think. Early AI systems were rule-based
and had limited capabilities. The field experienced several "AI winters" where progress stalled
due to unrealistic expectations and technical limitations.

### Modern Developments
The transformer architecture, introduced in 2017, marked another watershed moment.
Unlike previous models that processed sequences linearly, transformers could attend to all parts
of the input simultaneously. This parallel processing capability made them ideal for natural
language tasks. Today, large language models built on transformer architecture dominate the AI
landscape. These models can generate human-like text, answer questions, write code, and perform
countless other tasks.

## Applications
### Natural Language Processing
Modern NLP systems can understand context, generate coherent text, translate between languages,
and answer complex questions. Applications include chatbots, virtual assistants, and automated
content generation.

### Computer Vision
Computer vision has advanced significantly with deep learning. Systems can now recognize objects,
detect faces, analyze medical images, and enable autonomous vehicles. The accuracy of these
systems has reached or exceeded human performance in many tasks.

### Robotics
AI-powered robots are being deployed in manufacturing, healthcare, and service industries.
These systems combine perception, planning, and control to perform complex tasks autonomously.

## Challenges and Limitations
Despite significant progress, AI systems face several challenges:
- Data requirements: Many systems require massive amounts of training data
- Computational resources: Training large models requires substantial computing power
- Interpretability: Understanding how AI systems make decisions remains difficult
- Bias and fairness: AI systems can perpetuate or amplify existing biases
- Safety and security: Ensuring AI systems behave safely and securely is critical

## Future Directions
The future of AI holds promise for even more transformative applications. Research is ongoing
in areas such as:
- General artificial intelligence that can perform any intellectual task
- More efficient training methods that require less data and computation
- Better integration of symbolic and neural approaches
- Improved safety and alignment with human values

## Conclusion
Artificial intelligence continues to evolve and impact society in profound ways.
As the technology advances, it is important to consider both the opportunities and challenges
it presents. Responsible development and deployment of AI systems will be crucial for
maximizing benefits while minimizing risks.
""",
    
    'very_large': """
# Comprehensive Legal Document: Terms of Service Agreement

## 1. DEFINITIONS AND INTERPRETATION

### 1.1 Definitions
In this Agreement, unless the context otherwise requires, the following terms shall have the meanings
set forth below:

"Services" means the software services, applications, platforms, and related services provided by
Company under this Agreement, including but not limited to cloud-based solutions, APIs, mobile
applications, and web-based interfaces.

"User" means any person, entity, or organization that accesses or uses the Services, whether
directly or indirectly, including employees, contractors, agents, or representatives of an
organization that has entered into this Agreement.

"Confidential Information" means any information disclosed by one party to another, whether orally,
in writing, or in any other form, that is designated as confidential or that reasonably should be
understood to be confidential given the nature of the information and the circumstances of disclosure.

"Intellectual Property" means all intellectual property rights, including but not limited to
copyrights, trademarks, trade secrets, patents, and any other proprietary rights recognized in any
jurisdiction worldwide.

### 1.2 Interpretation
The headings in this Agreement are for convenience only and shall not affect its interpretation.
References to sections, clauses, and schedules are to sections, clauses, and schedules of this
Agreement. The singular includes the plural and vice versa.

## 2. GRANT OF LICENSE

### 2.1 License Scope
Subject to the terms and conditions of this Agreement, Company hereby grants to User a
non-exclusive, non-transferable, revocable license to use the Services solely for User's internal
business purposes in accordance with the documentation and within the scope of the subscription
plan selected by User.

### 2.2 License Restrictions
User shall not, and shall not permit any third party to:
(a) reverse engineer, decompile, disassemble, or otherwise attempt to derive the source code
    or underlying algorithms of the Services;
(b) rent, lease, lend, sell, sublicense, assign, or otherwise transfer the Services or any
    rights granted hereunder;
(c) remove, alter, or obscure any proprietary notices, labels, or marks on the Services;
(d) use the Services for any illegal, unauthorized, or prohibited purpose;
(e) interfere with or disrupt the integrity or performance of the Services;
(f) attempt to gain unauthorized access to the Services or related systems;
(g) use the Services to develop competing products or services;
(h) copy, modify, or create derivative works based on the Services.

### 2.3 Updates and Modifications
Company reserves the right to modify, update, or discontinue any aspect of the Services at any time.
Company will provide reasonable notice of material changes that adversely affect User's use of
the Services.

## 3. USER OBLIGATIONS

### 3.1 Account Security
User is responsible for maintaining the confidentiality of account credentials and for all
activities that occur under User's account. User agrees to immediately notify Company of any
unauthorized use of User's account or any other breach of security.

### 3.2 Compliance
User agrees to use the Services in compliance with all applicable laws, regulations, and industry
standards. User shall not use the Services in any manner that violates the rights of any third
party, including intellectual property rights, privacy rights, or publicity rights.

### 3.3 Data and Content
User retains all ownership rights in data and content that User provides to the Services.
User grants Company a limited license to use such data and content solely for the purpose of
providing and improving the Services. User represents and warrants that User has all necessary
rights to grant such license.

## 4. INTELLECTUAL PROPERTY

### 4.1 Company Ownership
All right, title, and interest in and to the Services, including all Intellectual Property
rights therein, are and will remain with Company and its licensors. This Agreement does not
grant User any rights to use Company's trademarks, service marks, logos, or other brand features.

### 4.2 User Feedback
If User provides any feedback, suggestions, or ideas regarding the Services, User hereby grants
Company a perpetual, irrevocable, worldwide, royalty-free license to use, modify, and incorporate
such feedback into the Services without any obligation to User.

## 5. FEES AND PAYMENT

### 5.1 Subscription Fees
User agrees to pay all fees associated with User's subscription plan in accordance with the
pricing terms set forth on Company's website or as otherwise agreed in writing. Fees are
non-refundable except as required by law or as expressly provided in this Agreement.

### 5.2 Payment Terms
All fees are due in advance for the subscription period. User authorizes Company to charge
User's payment method on file for all fees. If payment is not received by the due date,
Company may suspend or terminate User's access to the Services.

### 5.3 Price Changes
Company reserves the right to modify pricing at any time. Price changes will be effective at
the start of the next subscription period, and Company will provide at least thirty (30) days
notice of any price increases.

## 6. TERM AND TERMINATION

### 6.1 Term
This Agreement commences on the date User first accesses the Services and continues until
terminated in accordance with this section.

### 6.2 Termination by User
User may terminate this Agreement at any time by providing thirty (30) days written notice to
Company or by canceling User's subscription through the Services interface.

### 6.3 Termination by Company
Company may terminate this Agreement immediately upon written notice if:
(a) User breaches any material term of this Agreement and fails to cure such breach within
    thirty (30) days after receiving written notice;
(b) User becomes insolvent, files for bankruptcy, or ceases to conduct business;
(c) Company determines that User's use of the Services poses a security risk or violates
    applicable laws.

### 6.4 Effect of Termination
Upon termination, User's right to access and use the Services will immediately cease.
Company may delete User's data and content after a reasonable retention period, subject to
applicable legal requirements.

## 7. WARRANTIES AND DISCLAIMERS

### 7.1 Service Warranty
Company warrants that the Services will perform substantially in accordance with the
documentation under normal use conditions. Company's sole obligation for breach of this
warranty is to use commercially reasonable efforts to correct any material non-conformity.

### 7.2 Disclaimer
EXCEPT AS EXPRESSLY PROVIDED IN THIS AGREEMENT, THE SERVICES ARE PROVIDED "AS IS" AND "AS AVAILABLE"
WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

## 8. LIMITATION OF LIABILITY

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, COMPANY SHALL NOT BE LIABLE FOR ANY INDIRECT,
INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR REVENUES,
WHETHER INCURRED DIRECTLY OR INDIRECTLY, OR ANY LOSS OF DATA, USE, GOODWILL, OR OTHER INTANGIBLE
LOSSES, ARISING OUT OF OR RELATING TO THIS AGREEMENT OR THE USE OF THE SERVICES.

## 9. INDEMNIFICATION

User agrees to indemnify, defend, and hold harmless Company and its officers, directors,
employees, and agents from and against any claims, damages, losses, liabilities, and expenses
(including reasonable attorneys' fees) arising out of or relating to User's use of the Services,
violation of this Agreement, or infringement of any third-party rights.

## 10. GENERAL PROVISIONS

### 10.1 Governing Law
This Agreement shall be governed by and construed in accordance with the laws of the jurisdiction
in which Company is incorporated, without regard to its conflict of law provisions.

### 10.2 Entire Agreement
This Agreement constitutes the entire agreement between the parties regarding the subject matter
hereof and supersedes all prior or contemporaneous agreements, understandings, or communications.

### 10.3 Amendments
This Agreement may only be amended by a written instrument signed by both parties.

### 10.4 Severability
If any provision of this Agreement is held to be invalid or unenforceable, the remaining
provisions shall remain in full force and effect.

### 10.5 Assignment
User may not assign or transfer this Agreement without Company's prior written consent.
Company may assign this Agreement in connection with a merger, acquisition, or sale of assets.
""",
    
    'narrative_long': """
The evolution of human civilization has been marked by numerous technological revolutions,
each fundamentally transforming how we live, work, and interact with the world around us.
From the agricultural revolution that enabled settled societies to the industrial revolution
that mechanized production, each era has brought profound changes to human society.

The information age, beginning in the late 20th century, introduced computers and digital
networks that revolutionized communication and data processing. This era saw the development
of personal computers, the internet, and mobile devices that connected billions of people
worldwide. Information became instantly accessible, and global communication became seamless.

We are now entering what many call the age of artificial intelligence. Machine learning
algorithms can now recognize patterns in data that would be impossible for humans to detect.
Neural networks, inspired by the structure of the human brain, can learn from examples and
make predictions about complex phenomena. These systems are being deployed in fields ranging
from healthcare to finance, from transportation to entertainment.

The implications of artificial intelligence are far-reaching. On one hand, AI promises to
solve some of humanity's most pressing challenges: climate change, disease, poverty, and
resource scarcity. AI systems can analyze vast amounts of data to identify solutions that
would take humans lifetimes to discover. They can optimize systems for efficiency, predict
outcomes with remarkable accuracy, and automate tasks that are dangerous or repetitive.

However, the rise of AI also raises important questions about the future of work, privacy,
autonomy, and human agency. As machines become capable of performing tasks once thought
to require human intelligence, we must consider how to ensure that the benefits of AI are
distributed equitably and that human values are preserved in an increasingly automated world.

The development of artificial intelligence is not just a technological challenge but also
a social, ethical, and philosophical one. How we choose to develop and deploy AI systems
will shape the future of humanity in ways we are only beginning to understand. It is crucial
that we approach this transformation thoughtfully, with careful consideration of both the
opportunities and risks that AI presents.
"""
}


def create_mock_embedding_function():
    """Create a mock embedding function for semantic chunking"""
    import numpy as np
    import hashlib
    
    def mock_embedding(text: str) -> np.ndarray:
        # Deterministic mock embedding based on text hash
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        np.random.seed(hash_val)
        return np.random.rand(384).astype(np.float32)
    
    return mock_embedding


async def benchmark_strategy(
    strategy_name: str,
    document_name: str,
    document_text: str,
    config: ChunkingConfig,
    num_runs: int = 3
) -> BenchmarkResult:
    """Benchmark a single strategy on a document"""
    
    # Create chunker
    try:
        if strategy_name == 'semantic':
            chunker = SemanticChunking(
                config,
                embedding_function=create_mock_embedding_function()
            )
        elif strategy_name == 'llm_based':
            # Skip LLM-based if no LLM service available
            print(f"  Skipping {strategy_name} (requires LLM service)")
            return None
        elif strategy_name == 'agentic':
            # Skip agentic if no LLM service available
            print(f"  Skipping {strategy_name} (requires LLM service)")
            return None
        elif strategy_name == 'late_chunking':
            # Skip late chunking if no embedding service available
            print(f"  Skipping {strategy_name} (requires embedding service)")
            return None
        else:
            chunker = ChunkingFactory.create(strategy_name, config)
    except Exception as e:
        print(f"  Error creating {strategy_name}: {e}")
        return None
    
    # Run multiple times and average
    times = []
    memory_peaks = []
    memory_currents = []
    all_chunks = []
    
    for run in range(num_runs):
        # Start memory tracking
        tracemalloc.start()
        
        # Time the chunking
        start_time = time.perf_counter()
        try:
            chunks = await chunker.chunk(document_text)
        except Exception as e:
            print(f"  Error during chunking: {e}")
            tracemalloc.stop()
            return None
        
        end_time = time.perf_counter()
        processing_time = end_time - start_time
        
        # Get memory stats
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        times.append(processing_time)
        memory_peaks.append(peak / 1024 / 1024)  # Convert to MB
        memory_currents.append(current / 1024 / 1024)  # Convert to MB
        if run == 0:  # Keep chunks from first run
            all_chunks = chunks
    
    # Calculate statistics
    avg_time = statistics.mean(times)
    avg_memory_peak = statistics.mean(memory_peaks)
    avg_memory_current = statistics.mean(memory_currents)
    
    chunk_sizes = [chunk.size for chunk in all_chunks]
    if chunk_sizes:
        avg_chunk_size = statistics.mean(chunk_sizes)
        min_chunk_size = min(chunk_sizes)
        max_chunk_size = max(chunk_sizes)
        chunk_size_stddev = statistics.stdev(chunk_sizes) if len(chunk_sizes) > 1 else 0
        chunk_size_median = statistics.median(chunk_sizes)
    else:
        avg_chunk_size = min_chunk_size = max_chunk_size = chunk_size_stddev = chunk_size_median = 0
    
    document_size = len(document_text)
    chunks_per_second = len(all_chunks) / avg_time if avg_time > 0 else 0
    chars_per_second = document_size / avg_time if avg_time > 0 else 0
    
    return BenchmarkResult(
        strategy=strategy_name,
        document_name=document_name,
        document_size=document_size,
        chunks_created=len(all_chunks),
        avg_chunk_size=avg_chunk_size,
        min_chunk_size=min_chunk_size,
        max_chunk_size=max_chunk_size,
        processing_time=avg_time,
        memory_peak=avg_memory_peak,
        memory_current=avg_memory_current,
        chunks_per_second=chunks_per_second,
        chars_per_second=chars_per_second,
        chunk_size_stddev=chunk_size_stddev,
        chunk_size_median=chunk_size_median,
    )


async def run_benchmark_suite(
    strategies: Optional[List[str]] = None,
    documents: Optional[Dict[str, str]] = None,
    config: Optional[ChunkingConfig] = None,
    num_runs: int = 3
) -> BenchmarkSuite:
    """Run comprehensive benchmark suite"""
    
    if strategies is None:
        # Test all available strategies (excluding ones that need external services)
        strategies = ['fixed_size', 'recursive', 'document_based', 'semantic', 'hierarchical']
    
    if documents is None:
        documents = BENCHMARK_DOCUMENTS
    
    if config is None:
        config = ChunkingConfig(
            chunk_size=512,
            chunk_overlap=50,
            min_chunk_size=100
        )
    
    print("="*70)
    print("CHUNKING STRATEGIES PERFORMANCE BENCHMARK")
    print("="*70)
    print(f"\nStrategies: {', '.join(strategies)}")
    print(f"Documents: {', '.join(documents.keys())}")
    print(f"Runs per test: {num_runs}")
    print(f"Config: chunk_size={config.chunk_size}, overlap={config.chunk_overlap}")
    print("\n" + "="*70 + "\n")
    
    results = []
    total_tests = len(strategies) * len(documents)
    current_test = 0
    
    for strategy_name in strategies:
        print(f"Testing strategy: {strategy_name}")
        for doc_name, doc_text in documents.items():
            current_test += 1
            print(f"  [{current_test}/{total_tests}] {doc_name} ({len(doc_text)} chars)...", end=' ', flush=True)
            
            result = await benchmark_strategy(
                strategy_name,
                doc_name,
                doc_text,
                config,
                num_runs
            )
            
            if result:
                results.append(result)
                print(f"✓ {result.chunks_created} chunks, {result.processing_time*1000:.2f}ms")
            else:
                print("✗ Failed")
        
        print()
    
    suite = BenchmarkSuite(
        results=results,
        config={
            'chunk_size': config.chunk_size,
            'chunk_overlap': config.chunk_overlap,
            'min_chunk_size': config.min_chunk_size,
            'strategies_tested': strategies,
            'documents_tested': list(documents.keys()),
            'num_runs': num_runs
        }
    )
    
    return suite


def generate_plots(suite: BenchmarkSuite, output_dir: str = 'benchmark_results'):
    """Generate visualization plots from benchmark results"""
    if not HAS_PLOTTING:
        print("Skipping plot generation (matplotlib not available)")
        return
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Organize results by strategy and document
    by_strategy = defaultdict(list)
    by_document = defaultdict(list)
    
    for result in suite.results:
        by_strategy[result.strategy].append(result)
        by_document[result.document_name].append(result)
    
    # 1. Processing Time Comparison
    fig, ax = plt.subplots(figsize=(12, 6))
    strategies = sorted(by_strategy.keys())
    document_names = sorted(by_document.keys())
    
    x = np.arange(len(document_names))
    width = 0.15
    
    for i, strategy in enumerate(strategies):
        times = []
        for doc_name in document_names:
            doc_results = [r for r in by_strategy[strategy] if r.document_name == doc_name]
            if doc_results:
                times.append(doc_results[0].processing_time * 1000)  # Convert to ms
            else:
                times.append(0)
        
        offset = (i - len(strategies)/2) * width + width/2
        ax.bar(x + offset, times, width, label=strategy.replace('_', ' ').title())
    
    ax.set_xlabel('Document Size')
    ax.set_ylabel('Processing Time (ms)')
    ax.set_title('Processing Time by Strategy and Document Size')
    ax.set_xticks(x)
    ax.set_xticklabels(document_names)
    ax.legend()
    ax.set_yscale('log')
    plt.tight_layout()
    plt.savefig(output_path / 'processing_time_comparison.png', dpi=150)
    plt.close()
    
    # 2. Chunks Created Comparison
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for i, strategy in enumerate(strategies):
        chunks = []
        for doc_name in document_names:
            doc_results = [r for r in by_strategy[strategy] if r.document_name == doc_name]
            if doc_results:
                chunks.append(doc_results[0].chunks_created)
            else:
                chunks.append(0)
        
        offset = (i - len(strategies)/2) * width + width/2
        ax.bar(x + offset, chunks, width, label=strategy.replace('_', ' ').title())
    
    ax.set_xlabel('Document Size')
    ax.set_ylabel('Number of Chunks')
    ax.set_title('Chunks Created by Strategy and Document Size')
    ax.set_xticks(x)
    ax.set_xticklabels(document_names)
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path / 'chunks_created_comparison.png', dpi=150)
    plt.close()
    
    # 3. Throughput (chars/sec)
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for i, strategy in enumerate(strategies):
        throughput = []
        for doc_name in document_names:
            doc_results = [r for r in by_strategy[strategy] if r.document_name == doc_name]
            if doc_results:
                throughput.append(doc_results[0].chars_per_second / 1000)  # Convert to K chars/sec
            else:
                throughput.append(0)
        
        offset = (i - len(strategies)/2) * width + width/2
        ax.bar(x + offset, throughput, width, label=strategy.replace('_', ' ').title())
    
    ax.set_xlabel('Document Size')
    ax.set_ylabel('Throughput (K chars/sec)')
    ax.set_title('Processing Throughput by Strategy')
    ax.set_xticks(x)
    ax.set_xticklabels(document_names)
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path / 'throughput_comparison.png', dpi=150)
    plt.close()
    
    # 4. Memory Usage
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for i, strategy in enumerate(strategies):
        memory = []
        for doc_name in document_names:
            doc_results = [r for r in by_strategy[strategy] if r.document_name == doc_name]
            if doc_results:
                memory.append(doc_results[0].memory_peak)
            else:
                memory.append(0)
        
        offset = (i - len(strategies)/2) * width + width/2
        ax.bar(x + offset, memory, width, label=strategy.replace('_', ' ').title())
    
    ax.set_xlabel('Document Size')
    ax.set_ylabel('Peak Memory Usage (MB)')
    ax.set_title('Memory Usage by Strategy and Document Size')
    ax.set_xticks(x)
    ax.set_xticklabels(document_names)
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path / 'memory_usage_comparison.png', dpi=150)
    plt.close()
    
    # 5. Average Chunk Size Distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    
    strategy_avg_sizes = []
    strategy_labels = []
    
    for strategy in strategies:
        sizes = [r.avg_chunk_size for r in by_strategy[strategy]]
        if sizes:
            strategy_avg_sizes.append(sizes)
            strategy_labels.append(strategy.replace('_', ' ').title())
    
    if strategy_avg_sizes:
        bp = ax.boxplot(strategy_avg_sizes, tick_labels=strategy_labels, patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor('lightblue')
        
        ax.set_ylabel('Average Chunk Size (chars)')
        ax.set_title('Average Chunk Size Distribution by Strategy')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(output_path / 'chunk_size_distribution.png', dpi=150)
        plt.close()
    
    # 6. Performance Summary Heatmap
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    metrics = [
        ('Processing Time (ms)', 'processing_time', lambda x: x * 1000),
        ('Chunks Created', 'chunks_created', lambda x: x),
        ('Throughput (K chars/sec)', 'chars_per_second', lambda x: x / 1000),
        ('Memory Peak (MB)', 'memory_peak', lambda x: x),
    ]
    
    for idx, (metric_name, attr, transform) in enumerate(metrics):
        ax = axes[idx // 2, idx % 2]
        
        # Create matrix
        matrix = []
        for strategy in strategies:
            row = []
            for doc_name in document_names:
                doc_results = [r for r in by_strategy[strategy] if r.document_name == doc_name]
                if doc_results:
                    value = getattr(doc_results[0], attr)
                    row.append(transform(value))
                else:
                    row.append(0)
            matrix.append(row)
        
        im = ax.imshow(matrix, cmap='viridis', aspect='auto')
        ax.set_xticks(range(len(document_names)))
        ax.set_xticklabels(document_names, rotation=45, ha='right')
        ax.set_yticks(range(len(strategies)))
        ax.set_yticklabels([s.replace('_', ' ').title() for s in strategies])
        ax.set_title(metric_name)
        plt.colorbar(im, ax=ax)
    
    plt.tight_layout()
    plt.savefig(output_path / 'performance_heatmap.png', dpi=150)
    plt.close()
    
    print(f"\nPlots saved to: {output_path}/")


def print_summary(suite: BenchmarkSuite):
    """Print summary statistics"""
    print("\n" + "="*70)
    print("BENCHMARK SUMMARY")
    print("="*70)
    
    # Group by strategy
    by_strategy = defaultdict(list)
    for result in suite.results:
        by_strategy[result.strategy].append(result)
    
    for strategy, results in sorted(by_strategy.items()):
        print(f"\n{strategy.replace('_', ' ').title()}:")
        print(f"  Total tests: {len(results)}")
        if results:
            avg_time = statistics.mean([r.processing_time for r in results])
            avg_chunks = statistics.mean([r.chunks_created for r in results])
            avg_throughput = statistics.mean([r.chars_per_second for r in results])
            avg_memory = statistics.mean([r.memory_peak for r in results])
            
            print(f"  Avg processing time: {avg_time*1000:.2f} ms")
            print(f"  Avg chunks created: {avg_chunks:.1f}")
            print(f"  Avg throughput: {avg_throughput/1000:.2f} K chars/sec")
            print(f"  Avg memory peak: {avg_memory:.2f} MB")
    
    # Find fastest strategy
    strategy_times = defaultdict(list)
    for result in suite.results:
        strategy_times[result.strategy].append(result.processing_time)
    
    avg_times = {s: statistics.mean(times) for s, times in strategy_times.items()}
    fastest = min(avg_times.items(), key=lambda x: x[1])
    print(f"\nFastest strategy overall: {fastest[0]} ({fastest[1]*1000:.2f} ms avg)")


async def main():
    """Main benchmark execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Benchmark chunking strategies')
    parser.add_argument('--strategies', nargs='+', help='Strategies to test (default: all)')
    parser.add_argument('--documents', nargs='+', help='Documents to test (default: all)')
    parser.add_argument('--chunk-size', type=int, default=512, help='Chunk size (default: 512)')
    parser.add_argument('--overlap', type=int, default=50, help='Chunk overlap (default: 50)')
    parser.add_argument('--runs', type=int, default=3, help='Number of runs per test (default: 3)')
    parser.add_argument('--output', type=str, default='benchmark_results', help='Output directory')
    parser.add_argument('--no-plots', action='store_true', help='Skip plot generation')
    
    args = parser.parse_args()
    
    # Filter documents if specified
    documents = BENCHMARK_DOCUMENTS
    if args.documents:
        documents = {k: v for k, v in BENCHMARK_DOCUMENTS.items() if k in args.documents}
    
    # Create config
    config = ChunkingConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        min_chunk_size=100
    )
    
    # Run benchmarks
    suite = await run_benchmark_suite(
        strategies=args.strategies,
        documents=documents,
        config=config,
        num_runs=args.runs
    )
    
    # Save results
    output_path = Path(args.output)
    output_path.mkdir(exist_ok=True)
    
    json_path = output_path / 'benchmark_results.json'
    suite.save_json(str(json_path))
    print(f"\nResults saved to: {json_path}")
    
    # Print summary
    print_summary(suite)
    
    # Generate plots
    if not args.no_plots:
        generate_plots(suite, args.output)
    
    print("\n" + "="*70)
    print("BENCHMARK COMPLETE")
    print("="*70)


if __name__ == '__main__':
    asyncio.run(main())

