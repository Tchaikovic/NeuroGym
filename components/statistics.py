"""
Statistics page - displays user learning progress and performance metrics
"""
import streamlit as st
from database import get_user_statistics, quizzes_collection, get_user_xp, calculate_level

def show_statistics():
    """Display comprehensive learning statistics"""
    st.header("📊 Learning Statistics")
    user_email = st.session_state.user["email"]
    
    # Get statistics data
    stats = get_user_statistics(user_email)
    
    # Get XP data
    current_xp = get_user_xp(user_email)
    current_level = calculate_level(current_xp)
    
    # Display key metrics in columns
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Level", f"🎯 {current_level}")
    
    with col2:
        st.metric("Total XP", f"⭐ {current_xp}")
    
    with col3:
        st.metric("Topics Worked On", stats["topics_count"])
    
    with col4:
        st.metric("Quizzes Taken", stats["quizzes_taken"])
    
    with col5:
        st.metric("Correct Answers", stats["correct_answers"])
    
    # Overall accuracy percentage
    if stats["total_questions"] > 0:
        accuracy = (stats["correct_answers"] / stats["total_questions"]) * 100
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Overall Accuracy", f"{accuracy:.1f}%")
        with col2:
            st.metric("Incorrect Answers", stats["incorrect_answers"])
    
    # XP Progress section
    st.subheader("🚀 XP Progress")
    xp_current_level = current_xp - ((current_level - 1) * 100)
    progress = xp_current_level / 100.0
    st.write(f"**Level {current_level} Progress:** {xp_current_level}/100 XP")
    st.progress(progress)
    
    if current_level > 1:
        st.info(f"🎉 You've reached Level {current_level}! Keep learning to unlock Level {current_level + 1}!")
    
    # XP earning breakdown
    with st.expander("📊 How to Earn XP"):
        st.write("**XP Rewards:**")
        st.write("- 🔑 Daily login: **+5 XP**")
        st.write("- 📚 New topic: **+15 XP**")
        st.write("- 📝 Complete quiz: **+10 XP base**")
        st.write("- ✅ Correct answer: **+5 XP each**")
    
    # Topics breakdown
    if stats["topics_list"]:
        st.subheader("📚 Topics Breakdown")
        for topic_doc in stats["topics_list"]:
            topic_name = topic_doc["topic"]
            # Handle both 'created_date' (preferred) and legacy 'date' field names
            topic_date = topic_doc.get("created_date") or topic_doc.get("date", "Unknown date")
            
            # Count quizzes for this topic
            topic_quizzes = quizzes_collection.count_documents({"topic": topic_name})
            
            with st.expander(f"📖 {topic_name}"):
                st.write(f"**Started:** {topic_date[:10] if topic_date != 'Unknown date' else topic_date}")
                st.write(f"**Quizzes Created:** {topic_quizzes}")
    
    # Quiz performance breakdown
    if stats["quizzes_taken"] > 0:
        st.subheader("🎯 Quiz Performance")
        from database import answers_collection, get_quiz_by_id
        
        quiz_answers = list(answers_collection.find({"user_email": user_email}))
        for answer_doc in quiz_answers:
            quiz_id = answer_doc["quiz_id"]
            user_answers = answer_doc["answers"]
            
            quiz_doc = get_quiz_by_id(quiz_id)
            if quiz_doc:
                quiz_title = quiz_doc.get("title", "Untitled Quiz")
                quiz_topic = quiz_doc.get("topic", "Unknown Topic")
                quiz_difficulty = quiz_doc.get("difficulty", "Unknown")
                
                # Calculate score for this quiz
                quiz_correct = 0
                quiz_total = 0
                for i, question in enumerate(quiz_doc.get("questions", [])):
                    if i < len(user_answers):
                        quiz_total += 1
                        # Ensure question is a dictionary and has an 'answer' field
                        if isinstance(question, dict) and "answer" in question:
                            if user_answers[i] == question.get("answer"):
                                quiz_correct += 1
                
                with st.expander(f"🧩 {quiz_title} ({quiz_topic})"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Score:** {quiz_correct}/{quiz_total}")
                    with col2:
                        if quiz_total > 0:
                            quiz_accuracy = (quiz_correct / quiz_total) * 100
                            st.write(f"**Accuracy:** {quiz_accuracy:.1f}%")
                    with col3:
                        st.write(f"**Difficulty:** {quiz_difficulty}")
