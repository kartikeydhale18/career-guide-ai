import { useState, useRef, useEffect } from 'react';
import './App.css'; // Just keeping it so vite doesn't complain if main.jsx imports it

const generateSessionId = () => {
  return 'sess_' + Math.random().toString(36).substring(2, 15);
};

const featureContent = {
  career_advice: {
    title: "Career Guidance",
    desc: "Ask anything about your career path, industry trends, or skill development.",
    placeholder: "E.g. What skills do I need to become a Data Scientist?",
    welcome: "Hello! I'm your Career Guide AI. How can I help you propel your career forward today?",
    icon: "ph ph-compass"
  },
  resume_tip: {
    title: "Resume Builder",
    desc: "Get actionable advice on improving your resume structure and bullet points.",
    placeholder: "Paste a resume bullet point to improve, or ask for general tips...",
    welcome: "Ready to polish your resume! Paste a bullet point you want me to improve, or ask for structural advice.",
    icon: "ph ph-file-text"
  },
  interview_question: {
    title: "Interview Prep",
    desc: "Practice with realistic interview questions and get answering strategies.",
    placeholder: "E.g. Ask me a behavioral question for a Marketing role.",
    welcome: "Let's prep for your interview. What role are you interviewing for?",
    icon: "ph ph-microphone-stage"
  }
};

// Component for Alphabet Scramble Text
const ScrambleText = ({ text }) => {
  const [displayText, setDisplayText] = useState(text);
  
  useEffect(() => {
    let iteration = 0;
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    let interval = null;
    
    interval = setInterval(() => {
      setDisplayText(text.split("").map((letter, index) => {
        if(index < iteration) {
          return text[index];
        }
        if (letter === " ") return " ";
        return letters[Math.floor(Math.random() * 26)];
      }).join(""));
      
      if(iteration >= text.length){
        clearInterval(interval);
      }
      iteration += 1 / 2;
    }, 20);
    
    return () => clearInterval(interval);
  }, [text]);
  
  return <span>{displayText}</span>;
};

// Component for Chat Messages (Slide Up Animation)
const MessageBubble = ({ msg, formatResponse }) => {
  return (
    <div className={`message ${msg.type}-message slide-up-reveal`}>
      <div className="message-avatar">
        <i className={msg.type === 'user' ? "ph ph-user" : "ph-fill ph-robot"}></i>
      </div>
      <div className="message-content">
        {msg.type === 'user' ? (
          msg.content
        ) : (
          <span dangerouslySetInnerHTML={formatResponse(msg.content)} />
        )}
      </div>
    </div>
  );
};

// Component for Radial Button Ripple
const RippleButton = ({ children, isActive, onClick }) => {
  return (
    <button 
      className={`ripple-btn ${isActive ? 'active' : ''}`}
      onClick={onClick}
    >
      <span className="ripple-circle"></span>
      {children}
    </button>
  );
};

// Login Window Component
const LoginWindow = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      if (response.ok) {
        onLoginSuccess(username);
      } else {
        const data = await response.json();
        setError(data.detail || 'Login failed');
      }
    } catch (err) {
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-overlay">
      <div className="login-card">
        <div className="login-header">
          <i className="ph ph-briefcase"></i>
          <h2><ScrambleText text="Career Guide AI" /></h2>
          <p>Please log in to continue</p>
        </div>
        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label>Username</label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              required 
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
            />
          </div>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" disabled={loading} className="login-submit-btn">
            {loading ? 'Authenticating...' : 'Log In'}
          </button>
        </form>
      </div>
    </div>
  );
};


function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loggedInUser, setLoggedInUser] = useState('');

  const [sessionId] = useState(() => {
    let id = localStorage.getItem('career_ai_session');
    if (!id) {
      id = generateSessionId();
      localStorage.setItem('career_ai_session', id);
    }
    return id;
  });

  const [currentFeature, setCurrentFeature] = useState('career_advice');
  const [messages, setMessages] = useState([
    { type: 'system', content: featureContent['career_advice'].welcome }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleFeatureSwitch = (featureKey) => {
    if (currentFeature === featureKey) return;
    setCurrentFeature(featureKey);
    setMessages([
      { type: 'system', content: featureContent[featureKey].welcome }
    ]);
  };

  const formatResponse = (text) => {
    const formatted = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br/>');
    return { __html: formatted };
  };

  const handleInput = (e) => {
    setInputValue(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = e.target.scrollHeight + 'px';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const msg = inputValue.trim();
    if (!msg || isLoading) return;

    // Reset Input
    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    // Add user message
    setMessages(prev => [...prev, { type: 'user', content: msg }]);
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: msg,
          feature_type: currentFeature,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to communicate with AI');
      }

      const data = await response.json();
      setMessages(prev => [...prev, { type: 'system', content: data.response }]);
    } catch (error) {
      setMessages(prev => [...prev, { type: 'system', content: `⚠️ **Error:** ${error.message}. Please try again.` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const current = featureContent[currentFeature];

  if (!isAuthenticated) {
    return (
      <div className="app-container">
        <LoginWindow onLoginSuccess={(user) => {
          setLoggedInUser(user);
          setIsAuthenticated(true);
        }} />
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand">
          <i className="ph ph-briefcase"></i>
          <h1><ScrambleText text="Career Guide AI" /></h1>
        </div>
        
        <nav className="nav-menu">
          <p className="nav-title"><ScrambleText text="Features" /></p>
          {Object.entries(featureContent).map(([key, item]) => (
            <RippleButton 
              key={key}
              isActive={currentFeature === key}
              onClick={() => handleFeatureSwitch(key)}
            >
              <i className={item.icon}></i>
              <span className="btn-text"><ScrambleText text={item.title} /></span>
            </RippleButton>
          ))}
        </nav>

        <div className="user-info">
          <div className="avatar">
            <i className="ph ph-user"></i>
          </div>
          <div className="details">
            <span className="name">{loggedInUser || 'Admin User'}</span>
            <span className="status">Online</span>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="chat-area">
        <header className="chat-header">
          <div>
            <h2><ScrambleText text={current.title} /></h2>
            {/* ScrambleText removed from subtitle to keep it readable for long text */}
            <p>{current.desc}</p>
          </div>
        </header>

        <div className="messages-container" id="chat-messages">
          {messages.map((msg, idx) => (
            <MessageBubble key={idx} msg={msg} formatResponse={formatResponse} />
          ))}

          {isLoading && (
            <div className="message system-message slide-up-reveal" id="typing-indicator">
              <div className="message-avatar">
                <i className="ph-fill ph-robot"></i>
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <form className="chat-form" onSubmit={handleSubmit}>
            <div className="input-wrapper">
              <textarea 
                ref={textareaRef}
                value={inputValue}
                onChange={handleInput}
                onKeyDown={handleKeyDown}
                placeholder={current.placeholder} 
                rows="1" 
                required
              />
              <button type="submit" className="send-btn" aria-label="Send message" disabled={isLoading}>
                <i className="ph-fill ph-paper-plane-right"></i>
              </button>
            </div>
            <div className="footer-note">AI responses can be inaccurate. Always verify critical career decisions.</div>
          </form>
        </div>
      </main>
    </div>
  );
}

export default App;
