from typing import Callable, Dict, List, Any
from functools import wraps
from config import config
from pathlib import Path
import importlib
import pkgutil
import inspect

class ToolRegistry:
    """Registry central para todas as ferramentas do sistema"""
    _instance = None
    _tools: Dict[str, Callable] = {}
    _tool_instances: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register_tool(cls, func: Callable) -> Callable:
        """Registra uma função como ferramenta disponível"""
        cls._tools[func.__name__] = func
        return func
    
    @classmethod
    def register_tool_class(cls, tool_class: type) -> None:
        """
        Registra métodos marcados com @tool de uma classe.
        Cria UMA instância da classe e registra métodos bound.
        """
        # Criar instância única da classe
        instance = tool_class()
        
        # Procurar métodos marcados com @tool
        for method_name in dir(instance):
            if not method_name.startswith('_'):
                method = getattr(instance, method_name)
                if callable(method) and hasattr(method, '_is_tool'):
                    # O método já está bound (vinculado à instância)
                    # Não precisa de wrapper, só registrar direto
                    cls._tools[method_name] = method
                    cls._tool_instances[method_name] = instance
    
    @classmethod
    def get_all_tools(cls) -> List[Callable]:
        """Retorna todas as ferramentas registradas"""
        print(f'{config.emojis['loading']}{config.colors['dim']}Inicializando ferramentas...{config.colors['default']}')
        return list(cls._tools.values())
    
    @classmethod
    def clear_registry(cls):
        """Limpa o registry (útil para testes)"""
        cls._tools.clear()
        cls._tool_instances.clear()

def tool(func: Callable) -> Callable:
    """
    Decorator que registra automaticamente uma função como ferramenta.
    
    Usage:
        @tool
        def my_function(param1: str) -> str:
            '''Tool description'''
            return result
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # Marcar como tool para detecção automática
    wrapper._is_tool = True
    
    # Se for função livre (não método), registrar diretamente
    if not hasattr(func, '__self__'):
        ToolRegistry.register_tool(wrapper)
    
    return wrapper

def auto_load_tools(tools_package_name: str = 'Tools') -> List[Callable]:
    """
    Carrega automaticamente todas as ferramentas do pacote especificado.
    
    Args:
        tools_package_name: Nome do pacote contendo as ferramentas
        
    Returns:
        Lista de todas as ferramentas carregadas
    """
    # Limpa o registry antes de carregar
    ToolRegistry.clear_registry()
    
    try:
        # Importa o pacote principal
        tools_package = importlib.import_module(tools_package_name)
        package_path = Path(tools_package.__file__).parent if tools_package.__file__ else ""
        
        # Descobre e importa todos os módulos do pacote
        for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
            if module_name == 'tool_registry':  # Evita loop infinito
                continue
                
            full_module_name = f'{tools_package_name}.{module_name}'
            try:
                module = importlib.import_module(full_module_name)
                
                # Procura por classes no módulo
                for name in dir(module):
                    obj = getattr(module, name)
                    if (inspect.isclass(obj) and 
                        obj.__module__ == full_module_name and
                        not name.startswith('_')):
                        
                        # Verifica se a classe tem métodos marcados com @tool
                        has_tools = False
                        for method_name in dir(obj):
                            if not method_name.startswith('_'):
                                method = getattr(obj, method_name)
                                if callable(method) and hasattr(method, '_is_tool'):
                                    has_tools = True
                                    break
                        
                        if has_tools:
                            ToolRegistry.register_tool_class(obj)
                            
            except Exception:
                pass
                
        # Também procura por funções livres marcadas com @tool
        for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
            if module_name == 'tool_registry':
                continue
                
            full_module_name = f'{tools_package_name}.{module_name}'
            try:
                module = importlib.import_module(full_module_name)
                
                # Procura por funções livres
                for name in dir(module):
                    obj = getattr(module, name)
                    if (callable(obj) and 
                        hasattr(obj, '_is_tool') and
                        obj.__module__ == full_module_name and
                        not name.startswith('_') and
                        not inspect.isclass(obj)):
                        
                        ToolRegistry.register_tool(obj)
                        
            except Exception:
                pass
                
    except ImportError:
        pass
        
    tools = ToolRegistry.get_all_tools()
    return tools