# Cohere AI Tutor - Refactored Version

A comprehensive AI tutoring application built with Streamlit, Cohere AI, and MongoDB, featuring user authentication, persistent chat history, interactive quizzes, and progress analytics.

## 📁 Project Structure

```
cohere_agent/
├── streamlit_app.py      # Main application entry point
├── config.py             # Configuration settings and constants
├── database.py           # Database operations and MongoDB interactions
├── components/           # Modular page components
│   ├── auth.py          # Authentication (login/register)
│   ├── chat.py          # Main chat interface with AI tutor
│   ├── statistics.py    # Learning progress and analytics
│   └── sidebar.py       # Navigation and user info sidebar
└── main.py              # Original backend script (if needed)
```

## 🚀 Features

### Authentication System
- **User Registration**: Create account with name, age, email, password
- **User Login**: Secure authentication with persistent sessions
- **Personalized Experience**: AI tutor adapts to user's name and age

### AI Tutor Chat Interface
- **Natural Conversation Flow**: AI starts with casual chat to build rapport before academics
- **Smart Topic Suggestion**: After 2-3 exchanges, AI suggests working on topics with existing topic buttons
- **Intelligent Tutoring**: AI helps students with topics they struggle with
- **Interactive Quizzes**: Multiple-choice quizzes generated based on student topics
- **Inline Quiz Display**: Quizzes appear directly in chat conversation
- **Answer Recording**: Student responses saved with performance tracking
- **Immediate Feedback**: Instant scoring and mistake explanations
- **Topic Continuity**: Clickable buttons for previously studied topics

### Progress Analytics
- **Learning Statistics**: Comprehensive dashboard showing student progress
- **Performance Metrics**: Topics worked on, quizzes taken, accuracy rates
- **Topic Breakdown**: Detailed view of each subject studied
- **Quiz Performance**: Individual quiz results with scores and difficulty

### Data Persistence
- **MongoDB Integration**: All data stored persistently across sessions
- **Chat History**: Complete conversation history per user
- **Topic Tracking**: Automatic topic creation and linking to quizzes
- **Answer Storage**: All quiz responses recorded for analytics

## 🛠️ Technical Architecture

### Modular Design
The application is refactored into separate, focused modules:

- **`config.py`**: Centralized configuration management
- **`database.py`**: All MongoDB operations and data models
- **`components/`**: Individual page components with specific responsibilities
- **`streamlit_app.py`**: Main routing and session management

### Key Components

#### Database Layer (`database.py`)
- MongoDB connection and collection management
- User authentication functions
- Chat history serialization/deserialization
- Statistics data aggregation
- Quiz and answer management

#### Authentication (`components/auth.py`)
- Login and registration forms
- User validation and creation
- Session initialization
- Welcome message setup

#### Chat Interface (`components/chat.py`)
- AI conversation handling with natural conversation flow
- Tool function definitions (quiz creation, topic suggestion, search, calendar)
- Smart topic suggestion UI with clickable buttons for existing topics
- Quiz rendering and answer collection
- Cohere API integration with enhanced prompting

#### Statistics Dashboard (`components/statistics.py`)
- Performance metrics calculation
- Data visualization with Streamlit metrics
- Topic and quiz breakdowns
- Progress tracking displays

#### Navigation (`components/sidebar.py`)
- User information display
- Page navigation buttons
- Logout and session management
- Chat history clearing

## 📊 Database Schema

### Collections
- **users**: User accounts (email, password, name, age)
- **chats**: Persistent chat histories per user
- **topics**: Student topics with timestamps
- **quizzes**: Generated quizzes with questions and answers
- **answers**: Student quiz responses for analytics

### Data Relationships
- Topics ↔ Quizzes (via topic_id)
- Users ↔ All collections (via email/user_email)
- Quizzes ↔ Answers (via quiz_id)

## 🎯 Usage Flow

1. **Registration/Login**: User creates account or logs in
2. **Casual Conversation**: AI starts with friendly chat to build rapport
3. **Topic Suggestion**: After 2-3 exchanges, AI suggests academic topics with buttons for previous topics
4. **Topic Selection**: Student clicks existing topic button or types new topic
5. **Topic Storage**: System automatically stores new topics
6. **Quiz Generation**: AI creates relevant multiple-choice quiz
7. **Quiz Interaction**: Student answers questions inline
8. **Performance Tracking**: Results stored for analytics
9. **Progress Review**: Student can view statistics anytime

## 🔧 Configuration

Key settings in `config.py`:
- Cohere API credentials and model selection
- MongoDB connection parameters
- System prompt templates
- Collection naming conventions

## 🚀 Running the Application

```bash
# Install dependencies
pip install streamlit cohere pymongo

# Start MongoDB (if running locally)
mongod

# Run the application
streamlit run streamlit_app.py
```

## 📈 Benefits of Refactoring

### Code Organization
- **Separation of Concerns**: Each module has a specific responsibility
- **Maintainability**: Easier to update and debug individual components
- **Reusability**: Functions can be imported and reused across modules
- **Readability**: Cleaner, more focused code files

### Scalability
- **Modular Architecture**: Easy to add new pages or features
- **Configuration Management**: Centralized settings for easy deployment
- **Database Abstraction**: Clean separation between UI and data layers

### Development Experience
- **Easier Testing**: Individual components can be tested in isolation
- **Collaborative Development**: Team members can work on different modules
- **Code Reviews**: Smaller, focused files are easier to review
- **Documentation**: Clear structure makes the codebase self-documenting

This refactored version maintains all the original functionality while providing a much cleaner, more maintainable codebase that's ready for future enhancements and scaling.
