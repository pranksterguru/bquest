import yaml
import os
from cache.core_cache import get_core_cache

_config = None

def get_config(section=None, key=None):
    global _config
    
    filepath='./endurexconfig.yml'

    if _config is None: 
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        with open(filepath, 'r') as file:
            _config = yaml.safe_load(file)

    if section:
        section_data = _config.get(section)
        
        if section_data and key:
            keys = key.split(".")
            for k in keys:
                section_data = section_data.get(k)
                if section_data is None:
                    return None  
            return section_data

        return section_data
    
    return _config
