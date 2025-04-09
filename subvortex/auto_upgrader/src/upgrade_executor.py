class UpgradeExecutor:
    def rollout(self):
        pass

    def rollback(self):
        pass

    def _setup(self):
        pass

    def _mount(self):
        pass

    def _unmount(self):
        pass

def create_upgrade_executor():
    return UpgradeExecutor()