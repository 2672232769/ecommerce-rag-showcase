"""Local dense BGE-M3 inference with ONNX Runtime; no embedding API required."""
from pathlib import Path
from threading import Lock
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from langchain_core.embeddings import Embeddings


class LocalBgeM3Embeddings(Embeddings):
    """BGE-M3 INT8, CLS pooling + L2 normalization, 1024-dimensional dense vectors.

    The quantized ONNX export comes from onnx-community. Sparse/ColBERT outputs
    are not enabled; this is not a hybrid retriever.
    """

    def __init__(self, model_dir: str, max_tokens: int = 1024, threads: int = 4):
        directory = Path(model_dir)
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=max_tokens)
        self.tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(directory / "onnx" / "model_int8.onnx"),
            sess_options=options, providers=["CPUExecutionProvider"],
        )
        self.inputs = {entry.name for entry in self.session.get_inputs()}
        self.outputs = {entry.name: entry for entry in self.session.get_outputs()}
        if "last_hidden_state" not in self.outputs:
            raise ValueError("Unexpected BGE-M3 ONNX output schema")
        self.lock = Lock()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results = []
        # Bound batch size and concurrency to keep local CPU memory use predictable.
        with self.lock:
            for offset in range(0, len(texts), 4):
                encoded = self.tokenizer.encode_batch(texts[offset:offset + 4])
                tensors = {
                    "input_ids": np.asarray([item.ids for item in encoded], dtype=np.int64),
                    "attention_mask": np.asarray([item.attention_mask for item in encoded], dtype=np.int64),
                    "token_type_ids": np.asarray([item.type_ids for item in encoded], dtype=np.int64),
                }
                hidden = self.session.run(["last_hidden_state"], {key: value for key, value in tensors.items() if key in self.inputs})[0]
                vectors = hidden[:, 0].astype(np.float32)
                vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
                if vectors.shape[1] != 1024 or not np.isfinite(vectors).all():
                    raise ValueError("Invalid BGE-M3 dense vectors")
                results.extend(vectors.tolist())
        return results

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
