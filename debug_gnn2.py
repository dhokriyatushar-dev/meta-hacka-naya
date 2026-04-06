import traceback
with open('debug_err.txt', 'w', encoding='utf-8') as f:
    try:
        from gym_wrapper import GNNGymWrapper
        env = GNNGymWrapper(task_id='task1_easy', seed=42)
        env.reset(seed=42)
        env.step([0, 0])
    except Exception as e:
        traceback.print_exc(file=f)
