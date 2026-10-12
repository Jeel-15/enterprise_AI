# QLoRA Intent Classifier

- Base model: Qwen/Qwen2.5-1.5B-Instruct
- Method: QLoRA (NF4, double quant, paged_adamw_8bit), r=16, T4 GPU (Colab)
- Trainable params: 18,464,768 / 1,562,179,072 (1.18%)
- Peak GPU memory: ____ GB
- Baseline exact-match accuracy: ____%
- After QLoRA accuracy: ____% (fresh-load: 100%)
- Dataset: synthetic template-based (toy); eval uses unseen phrasings