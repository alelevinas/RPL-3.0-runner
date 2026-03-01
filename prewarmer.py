import docker
import logging
import time
import os
import json

class Prewarmer:
    def __init__(self, languages=None, network=None):
        self.client = docker.from_env()
        
        # Default languages if not provided
        default_languages = {
            "c_std11": "rpl-runner",
            "python_3.12": "rpl-runner"
        }
        
        # Load from env if available
        env_languages = os.getenv("RUNNER_LANGUAGES")
        if env_languages:
            try:
                self.languages = json.loads(env_languages)
            except Exception as e:
                logging.error(f"Failed to parse RUNNER_LANGUAGES env: {e}")
                self.languages = languages or default_languages
        else:
            self.languages = languages or default_languages
            
        self.pool = {lang: [] for lang in self.languages}
        self.pool_size = int(os.getenv("RUNNER_POOL_SIZE", "2"))
        self.network = network or os.getenv("RUNNER_NETWORK", "rpl_network")

    def prewarm(self):
        for lang, image in self.languages.items():
            # Check for existing containers in pool
            current_count = len(self.pool[lang])
            for _ in range(self.pool_size - current_count):
                try:
                    container = self.client.containers.create(
                        image, 
                        tty=True, 
                        detach=True,
                        network=self.network,
                        mem_limit=os.getenv("RUNNER_MEM_LIMIT", "512m"),
                        nano_cpus=int(os.getenv("RUNNER_CPU_LIMIT", "500000000")) # 0.5 CPU
                    )
                    container.start()
                    container.pause()
                    self.pool[lang].append(container)
                    logging.info(f"Pre-warmed container for {lang} (ID: {container.short_id})")
                except Exception as e:
                    logging.error(f"Failed to pre-warm container for {lang}: {e}")

    def get_container_url(self, lang):
        if lang in self.pool and self.pool[lang]:
            container = self.pool[lang].pop(0)
            try:
                container.unpause()
                # Refill pool in background to avoid blocking the worker
                import threading
                threading.Thread(target=self.prewarm).start()
                # Use container ID as hostname if on the same network
                return f"http://{container.id}:8000"
            except Exception as e:
                logging.error(f"Failed to unpause container {container.short_id}: {e}")
                return None
        return None

    def cleanup(self):
        for lang in self.pool:
            while self.pool[lang]:
                container = self.pool[lang].pop(0)
                try:
                    container.unpause()
                    container.stop()
                    container.remove()
                except Exception as e:
                    logging.warning(f"Failed to cleanup container: {e}")
