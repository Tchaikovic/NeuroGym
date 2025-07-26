"""
Performance profiler for NeuroGym AI Tutor
Tracks timing of different operations to identify bottlenecks
"""

import time
import functools
from typing import Dict, List, Optional
from datetime import datetime
import streamlit as st

class ChatProfiler:
    """Profile chat operations and track performance metrics"""
    
    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
        self.current_session: Dict[str, float] = {}
        self.enabled = True
        
    def start_timer(self, operation: str) -> None:
        """Start timing an operation"""
        if not self.enabled:
            return
        self.current_session[operation] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """End timing an operation and record the duration"""
        if not self.enabled or operation not in self.current_session:
            return 0.0
        
        duration = time.time() - self.current_session[operation]
        
        if operation not in self.timings:
            self.timings[operation] = []
        
        self.timings[operation].append(duration)
        del self.current_session[operation]
        
        return duration
    
    def profile_function(self, operation_name: str):
        """Decorator to profile a function"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                self.start_timer(operation_name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = self.end_timer(operation_name)
                    if self.enabled:
                        print(f"⏱️  {operation_name}: {duration:.3f}s")
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics"""
        stats = {}
        for operation, times in self.timings.items():
            if times:
                stats[operation] = {
                    'count': len(times),
                    'total': sum(times),
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'last': times[-1]
                }
        return stats
    
    def display_stats(self) -> None:
        """Display performance statistics in Streamlit"""
        stats = self.get_stats()
        if not stats:
            st.info("No profiling data available yet.")
            return
        
        st.subheader("🔍 Performance Profile")
        
        # Summary table
        import pandas as pd
        df_data = []
        total_time = 0
        
        for operation, data in stats.items():
            df_data.append({
                'Operation': operation,
                'Count': data['count'],
                'Total (s)': f"{data['total']:.3f}",
                'Average (s)': f"{data['average']:.3f}",
                'Min (s)': f"{data['min']:.3f}",
                'Max (s)': f"{data['max']:.3f}",
                'Last (s)': f"{data['last']:.3f}"
            })
            total_time += data['total']
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Performance insights
        if df_data:
            st.subheader("📊 Performance Insights")
            
            # Find slowest operations
            slowest_avg = max(stats.items(), key=lambda x: x[1]['average'])
            slowest_total = max(stats.items(), key=lambda x: x[1]['total'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Slowest Average", 
                    slowest_avg[0], 
                    f"{slowest_avg[1]['average']:.3f}s"
                )
            
            with col2:
                st.metric(
                    "Most Total Time", 
                    slowest_total[0], 
                    f"{slowest_total[1]['total']:.3f}s"
                )
            
            with col3:
                st.metric(
                    "Total Profiled Time", 
                    f"{total_time:.3f}s",
                    f"{len(stats)} operations"
                )
            
            # Recommendations
            st.subheader("💡 Optimization Recommendations")
            
            for operation, data in stats.items():
                if data['average'] > 2.0:  # Operations taking more than 2 seconds
                    st.warning(f"⚠️ **{operation}** is taking {data['average']:.3f}s on average - consider optimization")
                elif data['average'] > 1.0:  # Operations taking more than 1 second
                    st.info(f"ℹ️ **{operation}** could be optimized ({data['average']:.3f}s average)")
    
    def clear_stats(self) -> None:
        """Clear all timing statistics"""
        self.timings.clear()
        self.current_session.clear()
    
    def enable(self) -> None:
        """Enable profiling"""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable profiling"""
        self.enabled = False

# Global profiler instance
profiler = ChatProfiler()

# Context manager for easy timing
class timer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, show_result: bool = True):
        self.operation_name = operation_name
        self.show_result = show_result
    
    def __enter__(self):
        profiler.start_timer(self.operation_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = profiler.end_timer(self.operation_name)
        if self.show_result and profiler.enabled:
            print(f"⏱️  {self.operation_name}: {duration:.3f}s")

def profile_chat_operation(operation_name: str):
    """Decorator for profiling chat operations"""
    return profiler.profile_function(operation_name)

def get_profiler() -> ChatProfiler:
    """Get the global profiler instance"""
    return profiler
