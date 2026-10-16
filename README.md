# CareerLens 🎓 | Student Career Portal & Authentication System

A comprehensive, modern student placement and career management portal built with vanilla HTML5, CSS3, and JavaScript.

## 🚀 Live Demo & Features

### 1. 🔐 Student Authentication (Sign In & Sign Up)
- **Sign Up Form**:
  - Full Name, Department selection, Year of Study, College Name
  - 10-digit Phone Number validation
  - Email Address validation
  - Dynamic Real-Time Password Strength Meter (Weak / Fair / Good / Strong)
  - Confirm Password matching validation
  - Eye-toggle password visibility on all password fields
- **Sign In Form**:
  - Registered Email and Password authentication
  - "Remember my account" preference support
  - 1-Click "Auto-fill Demo" credentials for instant evaluation

### 2. 🔑 Interactive Forgot Password & OTP Flow
- Multi-step modal for password recovery
- In-app **6-digit verification code simulator banner** with 1-click **Auto-fill Code**
- Secure password reset and immediate login synchronization

### 3. 💼 Student Portal (Dashboard)
- Verified Student profile header with College, Department, Year, Email, and Phone badges
- **Resume Upload**: File browser selector ("Browse From Computer") and Drag & Drop file drop zone with format support for `.pdf`, `.doc`, `.docx` up to 10MB
- Attached file inspector with file size, badge, inspect/preview, and remove buttons
- **Professional & Coding Links Form**:
  - GitHub profile link with "Test" button
  - LinkedIn profile link with "Test" button
  - LeetCode profile link with "Test" button
  - Personal Portfolio website link with "Test" button
  - Prominent **"Save & Submit Career Details"** button
- **Live Recruiter Portfolio Showcase Card**:
  - Real-time live card reflecting saved details
  - Direct clickable badges for GitHub, LinkedIn, LeetCode, and Portfolio
  - One-click **Download Resume** button

## 📂 Project Structure

```text
├── index.html     # Semantic UI structure for Auth and Student Portal
├── style.css      # Ultra-modern dark glassmorphism design system
├── app.js         # Complete client-side logic, OTP simulator & LocalStorage DB
├── serve.js       # Zero-dependency local Node.js static server
└── README.md      # Project documentation
```

## 🛠️ How to Run Locally

1. Clone or download the repository:
   ```bash
   git clone https://github.com/swetha081206-blip/Hackathon.git
   cd Hackathon
   ```
2. Start the local server:
   ```bash
   node serve.js
   ```
3. Open your browser and navigate to:
   ```text
   http://localhost:8080/
   ```
   *(Or simply open `index.html` directly in any web browser!)*
