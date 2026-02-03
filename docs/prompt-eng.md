# Prompt Engineering Research Summary

This document summarizes findings from prompt engineering research, focusing on techniques that yield optimal results from Large Language Models (LLMs).

## Key Prompting Strategies & Findings

### Chain-of-Thought (CoT) Prompting
*   **Core Idea:** Elicits reasoning abilities by prompting the LLM to generate intermediate steps toward an answer.
*   **Method:** Provide a few examples of step-by-step reasoning in the prompt. This technique is particularly effective for models with sufficient scale.
*   **Impact:** Significantly improves performance on complex tasks like arithmetic, commonsense, and symbolic reasoning. It can achieve state-of-the-art results on benchmarks like GSM8K, even surpassing fine-tuned models with verifiers.
*   **Reference:** Wei et al. (2022) - "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (arXiv:2201.11903)

### Zero-Shot CoT Prompting
*   **Core Idea:** LLMs can perform reasoning tasks in a zero-shot manner simply by adding a specific phrase.
*   **Method:** Append phrases like "Let's think step by step." before the answer is generated.
*   **Impact:** Dramatically improves zero-shot performance across diverse reasoning tasks (arithmetic, symbolic, logical). Highlights inherent, untapped reasoning capabilities within LLMs that can be triggered by simple prompts.
*   **Reference:** Kojima et al. (2022) - "Large Language Models are Zero-Shot Reasoners" (arXiv:2205.11916)

### Self-Consistency
*   **Core Idea:** Enhances Chain-of-Thought prompting by sampling multiple reasoning paths and selecting the most consistent answer.
*   **Method:** Instead of taking a single greedy decoding path, generate diverse reasoning chains and aggregate the results (e.g., via majority voting).
*   **Impact:** Significantly boosts performance on reasoning benchmarks by leveraging the idea that complex problems often have multiple valid routes to a solution.
*   **Reference:** Wang et al. (2022) - "Self-Consistency Improves Chain of Thought Reasoning in Language Models" (arXiv:2203.11171)

### Least-to-Most Prompting
*   **Core Idea:** Breaks down complex problems into a series of simpler subproblems, solving them sequentially.
*   **Method:** Solve easier subproblems first, then use their solutions to inform and solve more difficult ones.
*   **Impact:** Enables LLMs to generalize to problems harder than those seen in few-shot examples, particularly effective for compositional reasoning tasks.
*   **Reference:** Zhou et al. (2022) - "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models" (arXiv:2205.10625)

### The Role of Demonstrations
*   **Core Idea:** Ground truth labels in few-shot examples may not be the primary drivers of in-context learning.
*   **Findings:** LLM performance is robust even when demonstration labels are randomized. Key factors include:
    *   **Label Space:** Showing the range of possible outputs.
    *   **Input Text Distribution:** Providing examples of typical inputs.
    *   **Sequence Format:** Demonstrating the structure of input-output pairs.
*   **Implication:** Demonstrations primarily provide structural and contextual cues, guiding the model on how to process information and format output, rather than just teaching specific correct answers.
*   **Reference:** Min et al. (2022) - "Rethinking the Role of Demonstrations: What Makes In-Context Learning Work?" (arXiv:2202.12837)

---

## Practical Prompting Guidelines

*   **Clarity and Structure:** Always aim for clear instructions and well-defined output formats. Consistent structure within prompts aids the model.
*   **Encourage Reasoning:** For complex tasks, explicitly ask the model to "think step by step," "show your work," or provide reasoning.
*   **Decomposition:** Break down highly complex requests into smaller, manageable subproblems (Least-to-Most).
*   **Consistency for Complex Tasks:** If a task requires intricate logical steps, consider generating multiple attempts and selecting the most coherent answer (Self-Consistency).
*   **Formatting:** The way information is presented (e.g., using bullet points, code blocks, clear delimiters) can influence comprehension.
*   **Urgency/Emphasis:** While direct keywords like "urgent" might prime a model, clear context and task definition are more critical than stylistic emphasis like all-caps or excessive punctuation. The model's interpretation of urgency is more nuanced than a direct command.

---
**Research Papers Fetched:**
- arXiv:2201.11903 (Chain-of-Thought Prompting)
- arXiv:2205.11916 (Zero-Shot CoT)
- arXiv:2203.11171 (Self-Consistency)
- arXiv:2205.10625 (Least-to-Most Prompting)
- arXiv:2202.12837 (Rethinking Demonstrations)

**Last Updated:** 2026-02-03
