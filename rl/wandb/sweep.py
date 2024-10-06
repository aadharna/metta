import wandb

def sweep_id_from_name(project: str, name: str) -> str:
    api = wandb.Api()
    sweeps = api.project(project).sweeps()
    for sweep in sweeps:
        if sweep.name == name:
            return sweep.id
    return None

def generate_run_id_for_sweep(sweep_id: str) -> str:
    api = wandb.Api()
    sweep = api.sweep(sweep_id)
    num_runs = len(sweep.runs)
    return f"{sweep.name}.r.{num_runs + 1}"

