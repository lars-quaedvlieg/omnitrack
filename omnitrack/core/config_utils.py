from typing import Any, Dict


def hydra_to_plain_config(cfg: Any) -> Dict:
    """
    Convert Hydra/OmegaConf or dataclasses to plain dict safely.
    Falls back to identity if already a dict-like.
    """
    try:
        from omegaconf import OmegaConf

        if OmegaConf.is_config(cfg):
            return OmegaConf.to_container(cfg, resolve=True, enum_to_str=True)  # type: ignore
    except Exception:
        pass

    # dataclass?
    try:
        from dataclasses import asdict, is_dataclass

        if is_dataclass(cfg):
            return asdict(cfg)  # type: ignore
    except Exception:
        pass

    # Mapping?
    if isinstance(cfg, dict):
        return dict(cfg)

    return {"config": str(cfg)}
