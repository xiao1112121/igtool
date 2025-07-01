"""
Temporary patch for blinker._saferef compatibility issue
"""

import sys
import warnings
import weakref
from typing import Any, Callable, Optional, Union

# Create a compatibility wrapper for WeakMethod to handle API differences
class BoundMethodWeakref:
    """Compatibility wrapper for WeakMethod with enhanced error handling"""
    
    def __init__(self, *args, **kwargs) -> None:
        # Handle different calling conventions and ignore unknown kwargs
        method = None
        callback = None
        
        # Extract method and callback from various argument patterns
        try:
            if args:
                if len(args) >= 1:
                    method = args[0]
                if len(args) >= 2:
                    callback = args[1]
                else:
                    callback = kwargs.get('callback', None)
            else:
                method = kwargs.get('method', None)
                callback = kwargs.get('callback', None)
            
            # Remove unsupported kwargs to avoid TypeError
            clean_kwargs = {}
            if callback is not None:
                clean_kwargs['callback'] = callback
                
        except Exception:
            # If argument parsing fails, create dummy ref
            self._weakref = lambda: None
            return
            
        if method is None:
            # If no method provided, create a dummy ref
            self._weakref = lambda: None
            return
            
        # Try multiple fallback strategies
        try:
            # Strategy 1: WeakMethod with callback
            if callback is not None:
                self._weakref: Union[weakref.WeakMethod[Any], weakref.ref[Any]] = weakref.WeakMethod(method, callback)
            else:
                self._weakref = weakref.WeakMethod(method)
        except (TypeError, AttributeError) as e1:
            try:
                # Strategy 2: Regular ref with callback
                if callback is not None:
                    self._weakref = weakref.ref(method, callback)
                else:
                    self._weakref = weakref.ref(method)
            except (TypeError, AttributeError) as e2:
                try:
                    # Strategy 3: Simple ref without callback
                    self._weakref = weakref.ref(method)
                except Exception as e3:
                    try:
                        # Strategy 4: Store method directly with lambda wrapper
                        self._weakref = lambda: method
                    except Exception as e4:
                        # Strategy 5: Ultimate fallback - return None
                        self._weakref = lambda: None
    
    def __call__(self) -> Any:
        try:
            return self._weakref()
        except:
            return None
    
    def __bool__(self) -> bool:
        try:
            return self._weakref() is not None
        except:
            return False
    
    def __eq__(self, other: Any) -> bool:
        try:
            if hasattr(other, '_weakref'):
                return self._weakref == other._weakref
            return False
        except:
            return False
    
    def __hash__(self) -> int:
        try:
            return hash(self._weakref)
        except:
            return 0

# Create a compatibility module for blinker._saferef
class SaferefModule:
    """Compatibility module for blinker._saferef"""
    
    def __getattr__(self, name):
        # For specific blinker._saferef functions, provide fallbacks
        if name == 'safe_ref':
            return weakref.ref
        elif name == 'BoundMethodWeakref':
            return BoundMethodWeakref
        elif name == 'ref':
            return weakref.ref
        elif name == 'proxy':
            return weakref.proxy
        elif name == 'callable':
            return callable
        
        # Import from weakref module as fallback
        if hasattr(weakref, name):
            return getattr(weakref, name)
        
        raise AttributeError(f"module 'blinker._saferef' has no attribute '{name}'")

# Monkey patch the missing module
if 'blinker._saferef' not in sys.modules:
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='seleniumwire')
    sys.modules['blinker._saferef'] = SaferefModule()
    print("[INFO] Applied enhanced blinker._saferef compatibility patch")

# Apply the patch immediately when imported
if __name__ == "__main__":
    print("✅ Enhanced Blinker compatibility patch applied successfully") 