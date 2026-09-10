"""唯一装配点：把具体基础设施注入应用服务与 Agent。"""

from dataclasses import dataclass
from pathlib import Path

from .agents.dating import DatingAgent
from .agents.legacy import LegacyAnalysisAgent
from .agents.matching import MatchingAgent
from .agents.profile import ProfileAgent
from .agents.romance import RomanceAgent
from .agents.tools import ToolExecutor
from .core.config import Settings
from .domain.ports import LanguageModel, Repository
from .infrastructure.ark import Ark
from .infrastructure.sqlite import Store
from .services.dating import DatingService
from .services.legacy import LegacyAnalysisService
from .services.sessions import SessionService


@dataclass
class Services:
    settings: Settings
    repository: Repository
    model: LanguageModel
    sessions: SessionService
    dating: DatingService
    legacy: LegacyAnalysisService
    romance: RomanceAgent

    async def aclose(self):
        await self.model.aclose()


def build_services(
    settings: Settings,
    repository: Repository | None = None,
    model: LanguageModel | None = None,
) -> Services:
    repository = repository if repository is not None else Store(settings.database_path)
    model = model if model is not None else Ark(settings.llm)
    tools = ToolExecutor(repository, ProfileAgent(model))
    return Services(
        settings,
        repository,
        model,
        SessionService(repository, MatchingAgent(model, tools)),
        DatingService(repository, DatingAgent(model)),
        LegacyAnalysisService(repository, LegacyAnalysisAgent(model)),
        RomanceAgent(
            model,
            (Path(__file__).parent / "agents/rules/romance.md").read_text(
                encoding="utf-8"
            ),
        ),
    )
