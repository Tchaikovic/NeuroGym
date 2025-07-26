"""
Performance Dashboard Component for NeuroGym AI Tutor
Displays real-time performance metrics and profiling data
"""

import streamlit as st
from profiler import profiler

def show_performance_dashboard():
    """Display performance dashboard in sidebar"""
    
    with st.sidebar:
        st.markdown("---")
        st.subheader("🔍 Performance Monitor")
        
        # Toggle profiling
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🟢 Enable" if not profiler.enabled else "🔴 Disable"):
                if profiler.enabled:
                    profiler.disable()
                    st.success("Profiling disabled")
                else:
                    profiler.enable()
                    st.success("Profiling enabled")
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear"):
                profiler.clear_stats()
                st.success("Stats cleared")
                st.rerun()
        
        # Status indicator
        status = "🟢 Active" if profiler.enabled else "🔴 Disabled"
        st.markdown(f"**Status:** {status}")
        
        # Quick stats
        stats = profiler.get_stats()
        if stats:
            st.markdown("**Quick Stats:**")
            
            # Find slowest operation
            slowest = max(stats.items(), key=lambda x: x[1]['last']) if stats else None
            if slowest:
                st.metric(
                    "Last Slowest", 
                    slowest[0][:15] + "..." if len(slowest[0]) > 15 else slowest[0],
                    f"{slowest[1]['last']:.3f}s"
                )
            
            # Total operations
            total_ops = sum(data['count'] for data in stats.values())
            st.metric("Total Operations", total_ops)
            
            # Average response time for API calls
            api_calls = [name for name in stats.keys() if 'cohere_api' in name]
            if api_calls:
                avg_api_time = sum(stats[name]['average'] for name in api_calls) / len(api_calls)
                st.metric("Avg API Time", f"{avg_api_time:.3f}s")
        else:
            st.info("No profiling data yet")
        
        # Show detailed stats button
        if st.button("📊 Show Detailed Stats"):
            st.session_state.show_performance_details = True
            st.rerun()

def show_detailed_performance():
    """Show detailed performance analysis"""
    if st.session_state.get('show_performance_details', False):
        st.markdown("---")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("🔍 Detailed Performance Analysis")
        with col2:
            if st.button("❌ Close"):
                st.session_state.show_performance_details = False
                st.rerun()
        
        profiler.display_stats()
        
        # Performance recommendations
        stats = profiler.get_stats()
        if stats:
            st.subheader("🚀 Performance Tips")
            
            # Identify bottlenecks
            slow_operations = [(name, data) for name, data in stats.items() if data['average'] > 1.0]
            
            if slow_operations:
                st.warning("**Potential Bottlenecks Found:**")
                for name, data in slow_operations:
                    if 'cohere_api' in name:
                        st.write(f"- **{name}**: {data['average']:.3f}s avg - Consider caching or optimizing prompts")
                    elif 'database' in name or 'mongo' in name:
                        st.write(f"- **{name}**: {data['average']:.3f}s avg - Consider database indexing")
                    elif 'tool_execution' in name:
                        st.write(f"- **{name}**: {data['average']:.3f}s avg - Consider optimizing tool logic")
                    else:
                        st.write(f"- **{name}**: {data['average']:.3f}s avg - Review implementation")
            else:
                st.success("✅ No significant bottlenecks detected!")
            
            # API usage insights
            api_stats = {name: data for name, data in stats.items() if 'cohere_api' in name}
            if api_stats:
                st.subheader("🌐 API Usage Analysis")
                
                total_api_time = sum(data['total'] for data in api_stats.values())
                total_api_calls = sum(data['count'] for data in api_stats.values())
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total API Time", f"{total_api_time:.2f}s")
                with col2:
                    st.metric("Total API Calls", total_api_calls)
                with col3:
                    if total_api_calls > 0:
                        avg_time = total_api_time / total_api_calls
                        st.metric("Avg per Call", f"{avg_time:.3f}s")
                
                # Show which API endpoints are most used
                for name, data in sorted(api_stats.items(), key=lambda x: x[1]['total'], reverse=True):
                    st.write(f"**{name}**: {data['count']} calls, {data['total']:.2f}s total, {data['average']:.3f}s avg")

def add_performance_monitoring():
    """Add performance monitoring to the app"""
    # Always show the sidebar dashboard
    show_performance_dashboard()
    
    # Show detailed view if requested
    show_detailed_performance()
