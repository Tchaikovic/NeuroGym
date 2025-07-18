"""
Statistics page - displays user learning progress and performance metrics
"""
import streamlit as st
from database import get_user_statistics, quizzes_collection

def show_statistics():
    """Display comprehensive learning statistics"""
    st.header("📊 Learning Statistics")
    user_email = st.session_state.user["email"]
    
    # Get statistics data
    stats = get_user_statistics(user_email)
    
    # Display key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Topics Worked On", stats["topics_count"])
    
    with col2:
        st.metric("Quizzes Taken", stats["quizzes_taken"])
    
    with col3:
        st.metric("Correct Answers", stats["correct_answers"])
    
    with col4:
        st.metric("Incorrect Answers", stats["incorrect_answers"])
    
    # Overall accuracy percentage
    if stats["total_questions"] > 0:
        accuracy = (stats["correct_answers"] / stats["total_questions"]) * 100
        st.metric("Overall Accuracy", f"{accuracy:.1f}%")
    
    # Topics breakdown
    if stats["topics_list"]:
        st.subheader("📚 Topics Breakdown")
        for topic_doc in stats["topics_list"]:
            topic_name = topic_doc["topic"]
            topic_date = topic_doc["date"]
            
            # Count quizzes for this topic
            topic_quizzes = quizzes_collection.count_documents({"topic": topic_name})
            
            with st.expander(f"📖 {topic_name}"):
                st.write(f"**Started:** {topic_date[:10]}")
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
