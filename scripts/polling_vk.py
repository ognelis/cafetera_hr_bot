"""Local development entry-point: VK bot in Long Poll mode.

Usage:
    uv run python scripts/polling_vk.py
"""

import atexit
import logging
import sys

# Allow running from project root
sys.path.insert(0, ".")

from app.config import Settings, configure_logging
from app.domain.qa_service import QAService
from app.integrations.vk.bot import create_bot
from app.integrations.vk.handlers import set_qa_service
from app.rag.chain import build_llm, build_rag_chain
from app.rag.prompts import GLOBAL_EXPERTS_PROMPT
from app.rag.retriever import build_embeddings, build_qdrant_client, build_retriever

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    bot = create_bot(settings)

    # Create shared resources once and pass to QAService
    qdrant_client = build_qdrant_client(settings)
    embeddings = build_embeddings(settings)
    llm = build_llm(settings)
    retriever = build_retriever(settings, qdrant_client=qdrant_client, embeddings=embeddings)
    chain = build_rag_chain(retriever, llm, system_prompt=GLOBAL_EXPERTS_PROMPT)
    qa = QAService(
        chain=chain,
        qdrant_client=qdrant_client,
        embeddings=embeddings,
        llm=llm,
        settings=settings,
    )
    set_qa_service(qa)

    def cleanup():
        qa.close()
        qdrant_client.close()

    atexit.register(cleanup)

    logger.info("Starting VK bot in Long Poll mode …")
    bot.run_forever()


if __name__ == "__main__":
    main()
