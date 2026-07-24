"""重试失败的 URL"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from batch_translate import process_url

urls = [
    "https://hermes-agent.nousresearch.com/docs/reference/faq",
    "https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban",
    "https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-tutorial",
    "https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks",
    "https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-worker-lanes",
    "https://hermes-agent.nousresearch.com/docs/user-guide/messaging/yuanbao",
    "https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/research/research-research-paper-writing",
    "https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/finance/finance-dcf-model",
    "https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-torchtitan",
    "https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/productivity/productivity-memento-flashcards",
]

for url in urls:
    print(process_url(url))
