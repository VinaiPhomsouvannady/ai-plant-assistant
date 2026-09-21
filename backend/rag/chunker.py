def chunk_text(text: str, words_per_chunk: int = 55) -> list[str]:
    words = text.split()
    return [
        " ".join(words[index:index + words_per_chunk])
        for index in range(0, len(words), words_per_chunk)
    ]
