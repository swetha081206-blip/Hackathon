/**
 * CareerLens - Student Portal & Authentication System
 * Features:
 * - Student Sign In & Sign Up with full academic details
 * - Interactive Forgot Password with 6-digit verification code simulator
 * - Student Portal with Resume Browser/Uploader & Coding Profiles (GitHub, LinkedIn, LeetCode, Portfolio)
 * - Real-time Live Recruiter Showcase Card
 * - Persistent LocalStorage Database
 */

(function () {
  'use strict';

  // ==========================================================================
  // Storage Keys & Seed Data
  // ==========================================================================
  const USERS_STORAGE_KEY = 'careerlens_students_db';
  const CURRENT_USER_KEY = 'careerlens_current_student';
  const REMEMBER_KEY = 'careerlens_remembered_email';

  // Seed default demo student if storage is empty
  const defaultDemoStudent = {
    name: 'Swetha Ramesh',
    department: 'Computer Science and Engineering (CSE)',
    year: '3rd Year',
    college: 'Anna University, Chennai',
    phone: '9876543210',
    email: 'swetha@college.edu',
    password: 'Password@123',
    career: {
      resume: {
        name: 'Swetha_Ramesh_Resume_2026.pdf',
        size: '1.4 MB',
        type: 'application/pdf',
        dataUrl: ''
      },
      github: 'https://github.com/swetha-ramesh',
      linkedin: 'https://linkedin.com/in/swetha-ramesh',
      leetcode: 'https://leetcode.com/u/swetha_coder',
      portfolio: 'https://swetha-portfolio.dev'
    }
  };

  function initDatabase() {
    const existing = localStorage.getItem(USERS_STORAGE_KEY);
    if (!existing) {
      const initialUsers = [defaultDemoStudent];
      localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(initialUsers));
    }
  }

  function getUsers() {
    try {
      return JSON.parse(localStorage.getItem(USERS_STORAGE_KEY)) || [];
    } catch (e) {
      return [];
    }
  }

  function saveUsers(users) {
    localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users));
  }

  function getCurrentUser() {
    try {
      return JSON.parse(localStorage.getItem(CURRENT_USER_KEY)) || null;
    } catch (e) {
      return null;
    }
  }

  function setCurrentUser(user) {
    if (user) {
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(CURRENT_USER_KEY);
    }
  }

  // ==========================================================================
  // DOM Elements Selection
  // ==========================================================================
  const authView = document.getElementById('authView');
  const portalView = document.getElementById('portalView');
  const navLogoutBtn = document.getElementById('navLogoutBtn');

  // Tabs
  const tabSignIn = document.getElementById('tabSignIn');
  const tabSignUp = document.getElementById('tabSignUp');
  const signInSection = document.getElementById('signInSection');
  const signUpSection = document.getElementById('signUpSection');
  const switchToSignUp = document.getElementById('switchToSignUp');
  const switchToSignIn = document.getElementById('switchToSignIn');

  // Sign In Elements
  const signInForm = document.getElementById('signInForm');
  const loginEmail = document.getElementById('loginEmail');
  const loginPassword = document.getElementById('loginPassword');
  const rememberMe = document.getElementById('rememberMe');
  const fillDemoBtn = document.getElementById('fillDemoBtn');

  // Sign Up Elements
  const signUpForm = document.getElementById('signUpForm');
  const regName = document.getElementById('regName');
  const regDepartment = document.getElementById('regDepartment');
  const regYear = document.getElementById('regYear');
  const regCollege = document.getElementById('regCollege');
  const regPhone = document.getElementById('regPhone');
  const regEmail = document.getElementById('regEmail');
  const regPassword = document.getElementById('regPassword');
  const regConfirmPassword = document.getElementById('regConfirmPassword');
  const regStrengthMeter = document.getElementById('regStrengthMeter');
  const regStrengthText = document.getElementById('regStrengthText');

  // Forgot Password Elements
  const openForgotBtn = document.getElementById('openForgotBtn');
  const closeForgotBtn = document.getElementById('closeForgotBtn');
  const forgotPasswordModal = document.getElementById('forgotPasswordModal');
  const forgotStep1 = document.getElementById('forgotStep1');
  const forgotStep2 = document.getElementById('forgotStep2');
  const forgotEmail = document.getElementById('forgotEmail');
  const sendOtpBtn = document.getElementById('sendOtpBtn');
  const sentEmailSpan = document.getElementById('sentEmailSpan');
  const displayGeneratedCode = document.getElementById('displayGeneratedCode');
  const quickFillCodeBtn = document.getElementById('quickFillCodeBtn');
  const resetPasswordForm = document.getElementById('resetPasswordForm');
  const verificationCode = document.getElementById('verificationCode');
  const newPassword = document.getElementById('newPassword');
  const confirmNewPassword = document.getElementById('confirmNewPassword');

  // Student Portal Elements
  const portalAvatar = document.getElementById('portalAvatar');
  const portalStudentName = document.getElementById('portalStudentName');
  const portalCollegeName = document.getElementById('portalCollegeName');
  const portalDepartment = document.getElementById('portalDepartment');
  const portalYear = document.getElementById('portalYear');
  const portalEmail = document.getElementById('portalEmail');
  const portalPhone = document.getElementById('portalPhone');

  // Career Form Elements
  const careerProfileForm = document.getElementById('careerProfileForm');
  const resumeDropZone = document.getElementById('resumeDropZone');
  const resumeFileInput = document.getElementById('resumeFileInput');
  const browseFileBtn = document.getElementById('browseFileBtn');
  const dropZonePrompt = document.getElementById('dropZonePrompt');
  const attachedFileInfo = document.getElementById('attachedFileInfo');
  const fileNameDisplay = document.getElementById('fileNameDisplay');
  const fileSizeDisplay = document.getElementById('fileSizeDisplay');
  const fileTypeIcon = document.getElementById('fileTypeIcon');
  const previewResumeBtn = document.getElementById('previewResumeBtn');
  const removeResumeBtn = document.getElementById('removeResumeBtn');

  // Links Elements
  const githubLink = document.getElementById('githubLink');
  const linkedinLink = document.getElementById('linkedinLink');
  const leetcodeLink = document.getElementById('leetcodeLink');
  const portfolioLink = document.getElementById('portfolioLink');

  // Recruiter Showcase Elements
  const showcaseAvatar = document.getElementById('showcaseAvatar');
  const showcaseName = document.getElementById('showcaseName');
  const showcaseCollege = document.getElementById('showcaseCollege');
  const showcaseDept = document.getElementById('showcaseDept');
  const showcaseResumeName = document.getElementById('showcaseResumeName');
  const downloadResumeAction = document.getElementById('downloadResumeAction');

  const showcaseGithubLink = document.getElementById('showcaseGithubLink');
  const showcaseLinkedinLink = document.getElementById('showcaseLinkedinLink');
  const showcaseLeetcodeLink = document.getElementById('showcaseLeetcodeLink');
  const showcasePortfolioLink = document.getElementById('showcasePortfolioLink');

  // Toast Container
  const toastContainer = document.getElementById('toastContainer');

  // In-memory state
  let currentActiveOtp = null;
  let targetResetEmail = '';
  let temporaryUploadedResume = null;

  // ==========================================================================
  // Toast Notification Engine
  // ==========================================================================
  function showToast(title, message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '⚠️';
    
    toast.innerHTML = `
      <div class="toast-icon">${icon}</div>
      <div class="toast-content">
        <span class="toast-title">${title}</span>
        <span class="toast-msg">${message}</span>
      </div>
      <button type="button" class="toast-close" aria-label="Close notification">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
      toast.remove();
    });

    toastContainer.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
      }
    }, duration);
  }

  // ==========================================================================
  // Helper Functions
  // ==========================================================================
  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function isValidPhone(phone) {
    return /^[6-9]\d{9}$/.test(phone.replace(/\D/g, ''));
  }

  function isValidUrl(url) {
    if (!url) return false;
    try {
      new URL(url);
      return true;
    } catch (_) {
      return false;
    }
  }

  function getInitials(name) {
    if (!name) return 'ST';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function clearError(elemId) {
    const errSpan = document.getElementById(elemId);
    if (errSpan) errSpan.textContent = '';
  }

  function setError(elemId, msg) {
    const errSpan = document.getElementById(elemId);
    if (errSpan) errSpan.textContent = msg;
  }

  // ==========================================================================
  // Tab Switching (Sign In <-> Sign Up)
  // ==========================================================================
  function showTab(tabName) {
    if (tabName === 'signin') {
      tabSignIn.classList.add('active');
      tabSignUp.classList.remove('active');
      signInSection.classList.remove('hidden');
      signUpSection.classList.add('hidden');
    } else {
      tabSignUp.classList.add('active');
      tabSignIn.classList.remove('active');
      signUpSection.classList.remove('hidden');
      signInSection.classList.add('hidden');
    }
  }

  tabSignIn.addEventListener('click', () => showTab('signin'));
  tabSignUp.addEventListener('click', () => showTab('signup'));
  switchToSignUp.addEventListener('click', () => showTab('signup'));
  switchToSignIn.addEventListener('click', () => showTab('signin'));

  // Password visibility toggle helper
  document.querySelectorAll('.password-toggle').forEach(btn => {
    btn.addEventListener('click', function () {
      const targetId = this.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (!input) return;

      if (input.type === 'password') {
        input.type = 'text';
        this.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
          </svg>
        `;
      } else {
        input.type = 'password';
        this.innerHTML = `
          <svg class="eye-open" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
        `;
      }
    });
  });

  // Password strength meter evaluation
  regPassword.addEventListener('input', function () {
    const val = this.value;
    let strength = 0;

    if (val.length >= 6) strength += 1;
    if (/[A-Z]/.test(val)) strength += 1;
    if (/[0-9]/.test(val)) strength += 1;
    if (/[^A-Za-z0-9]/.test(val)) strength += 1;

    regStrengthMeter.className = 'strength-indicator';

    if (val.length === 0) {
      regStrengthText.textContent = 'Password strength: Weak';
      return;
    }

    if (strength <= 1) {
      regStrengthMeter.classList.add('weak');
      regStrengthText.textContent = 'Password strength: Weak';
    } else if (strength === 2) {
      regStrengthMeter.classList.add('fair');
      regStrengthText.textContent = 'Password strength: Fair';
    } else if (strength === 3) {
      regStrengthMeter.classList.add('good');
      regStrengthText.textContent = 'Password strength: Good';
    } else {
      regStrengthMeter.classList.add('strong');
      regStrengthText.textContent = 'Password strength: Strong 💪';
    }
  });

  // Auto-fill demo button
  fillDemoBtn.addEventListener('click', () => {
    loginEmail.value = 'swetha@college.edu';
    loginPassword.value = 'Password@123';
    showToast('Demo Credentials Loaded', 'Click "Sign In to Student Portal" to enter', 'info');
  });

  // ==========================================================================
  // SIGN IN LOGIC
  // ==========================================================================
  signInForm.addEventListener('submit', function (e) {
    e.preventDefault();

    clearError('loginEmailError');
    clearError('loginPasswordError');

    const email = loginEmail.value.trim().toLowerCase();
    const password = loginPassword.value;

    let hasError = false;

    if (!email) {
      setError('loginEmailError', 'Please enter your registered email');
      hasError = true;
    } else if (!isValidEmail(email)) {
      setError('loginEmailError', 'Please enter a valid email format');
      hasError = true;
    }

    if (!password) {
      setError('loginPasswordError', 'Please enter your password');
      hasError = true;
    }

    if (hasError) return;

    const users = getUsers();
    const user = users.find(u => u.email.toLowerCase() === email);

    if (!user) {
      setError('loginEmailError', 'No account found with this email address');
      showToast('Account Not Found', 'Please sign up or check your email', 'error');
      return;
    }

    if (user.password !== password) {
      setError('loginPasswordError', 'Incorrect password. Click "Forgot Password?" to reset.');
      showToast('Authentication Failed', 'Incorrect password entered', 'error');
      return;
    }

    // Remember email logic
    if (rememberMe.checked) {
      localStorage.setItem(REMEMBER_KEY, email);
    } else {
      localStorage.removeItem(REMEMBER_KEY);
    }

    // Successful login
    setCurrentUser(user);
    showToast('Welcome Back!', `Signed in as ${user.name}`, 'success');
    renderPortal(user);
  });

  // ==========================================================================
  // SIGN UP LOGIC
  // ==========================================================================
  signUpForm.addEventListener('submit', function (e) {
    e.preventDefault();

    clearError('regNameError');
    clearError('regDeptError');
    clearError('regYearError');
    clearError('regCollegeError');
    clearError('regPhoneError');
    clearError('regEmailError');
    clearError('regPasswordError');
    clearError('regConfirmPasswordError');

    const name = regName.value.trim();
    const department = regDepartment.value;
    const year = regYear.value;
    const college = regCollege.value.trim();
    const phone = regPhone.value.trim();
    const email = regEmail.value.trim().toLowerCase();
    const password = regPassword.value;
    const confirmPassword = regConfirmPassword.value;

    let hasError = false;

    if (!name || name.length < 2) {
      setError('regNameError', 'Please enter your full name');
      hasError = true;
    }

    if (!department) {
      setError('regDeptError', 'Please select your department');
      hasError = true;
    }

    if (!year) {
      setError('regYearError', 'Please select your year of study');
      hasError = true;
    }

    if (!college || college.length < 3) {
      setError('regCollegeError', 'Please enter your college name');
      hasError = true;
    }

    if (!isValidPhone(phone)) {
      setError('regPhoneError', 'Please enter a valid 10-digit mobile number');
      hasError = true;
    }

    if (!isValidEmail(email)) {
      setError('regEmailError', 'Please enter a valid email address');
      hasError = true;
    }

    if (password.length < 6) {
      setError('regPasswordError', 'Password must be at least 6 characters long');
      hasError = true;
    }

    if (password !== confirmPassword) {
      setError('regConfirmPasswordError', 'Passwords do not match');
      hasError = true;
    }

    if (hasError) return;

    const users = getUsers();
    const existing = users.find(u => u.email.toLowerCase() === email);

    if (existing) {
      setError('regEmailError', 'An account with this email already exists. Please Sign In.');
      showToast('Registration Error', 'Email is already registered', 'error');
      return;
    }

    const newStudent = {
      name,
      department,
      year,
      college,
      phone,
      email,
      password,
      career: {
        resume: null,
        github: '',
        linkedin: '',
        leetcode: '',
        portfolio: ''
      }
    };

    users.push(newStudent);
    saveUsers(users);

    showToast('Registration Successful!', 'Account created. You can now sign in.', 'success');
    signUpForm.reset();
    regStrengthMeter.className = 'strength-indicator';
    regStrengthText.textContent = 'Password strength: Weak';

    // Pre-fill email in Sign In and navigate
    loginEmail.value = email;
    showTab('signin');
  });

  // ==========================================================================
  // FORGOT PASSWORD MODAL & VERIFICATION FLOW
  // ==========================================================================
  openForgotBtn.addEventListener('click', () => {
    forgotEmail.value = loginEmail.value.trim();
    forgotStep1.classList.remove('hidden');
    forgotStep2.classList.add('hidden');
    clearError('forgotEmailError');
    clearError('verificationCodeError');
    clearError('newPasswordError');
    clearError('confirmNewPasswordError');
    resetPasswordForm.reset();
    forgotPasswordModal.classList.remove('hidden');
  });

  closeForgotBtn.addEventListener('click', () => {
    forgotPasswordModal.classList.add('hidden');
  });

  forgotPasswordModal.addEventListener('click', (e) => {
    if (e.target === forgotPasswordModal) {
      forgotPasswordModal.classList.add('hidden');
    }
  });

  // Step 1: Send 6-digit code
  sendOtpBtn.addEventListener('click', () => {
    clearError('forgotEmailError');
    const email = forgotEmail.value.trim().toLowerCase();

    if (!email) {
      setError('forgotEmailError', 'Please enter your registered email address');
      return;
    }

    if (!isValidEmail(email)) {
      setError('forgotEmailError', 'Please enter a valid email format');
      return;
    }

    const users = getUsers();
    const user = users.find(u => u.email.toLowerCase() === email);

    if (!user) {
      setError('forgotEmailError', 'No account found with this email');
      return;
    }

    // Generate 6 digit code
    currentActiveOtp = Math.floor(100000 + Math.random() * 900000).toString();
    targetResetEmail = email;

    sentEmailSpan.textContent = email;
    displayGeneratedCode.textContent = currentActiveOtp;

    forgotStep1.classList.add('hidden');
    forgotStep2.classList.remove('hidden');

    showToast('Verification Code Sent', `Security code sent to ${email}`, 'success');
  });

  // Quick auto-fill code button in simulator banner
  quickFillCodeBtn.addEventListener('click', () => {
    if (currentActiveOtp) {
      verificationCode.value = currentActiveOtp;
      clearError('verificationCodeError');
      showToast('Code Auto-filled', `Entered ${currentActiveOtp}`, 'info');
    }
  });

  // Step 2: Validate code & Change Password
  resetPasswordForm.addEventListener('submit', function (e) {
    e.preventDefault();

    clearError('verificationCodeError');
    clearError('newPasswordError');
    clearError('confirmNewPasswordError');

    const enteredCode = verificationCode.value.trim();
    const newPass = newPassword.value;
    const confirmPass = confirmNewPassword.value;

    let hasError = false;

    if (enteredCode !== currentActiveOtp) {
      setError('verificationCodeError', 'Invalid 6-digit verification code. Please check simulator.');
      hasError = true;
    }

    if (newPass.length < 6) {
      setError('newPasswordError', 'New password must be at least 6 characters');
      hasError = true;
    }

    if (newPass !== confirmPass) {
      setError('confirmNewPasswordError', 'Passwords do not match');
      hasError = true;
    }

    if (hasError) return;

    // Update password in users DB
    const users = getUsers();
    const userIndex = users.findIndex(u => u.email.toLowerCase() === targetResetEmail);

    if (userIndex !== -1) {
      users[userIndex].password = newPass;
      saveUsers(users);

      // If resetting currently active user
      const currentUser = getCurrentUser();
      if (currentUser && currentUser.email.toLowerCase() === targetResetEmail) {
        currentUser.password = newPass;
        setCurrentUser(currentUser);
      }

      showToast('Password Changed Successfully', 'You can now sign in with your new password', 'success');
      forgotPasswordModal.classList.add('hidden');
      loginEmail.value = targetResetEmail;
      loginPassword.value = newPass;
      showTab('signin');
    } else {
      showToast('Error', 'Unable to find user account to reset', 'error');
    }
  });

  // ==========================================================================
  // STUDENT PORTAL (ஸ்டூடண்ட் போர்டல்) LOGIC
  // ==========================================================================
  function renderPortal(user) {
    authView.classList.add('hidden');
    portalView.classList.remove('hidden');
    navLogoutBtn.classList.remove('hidden');

    // Header info
    const initials = getInitials(user.name);
    portalAvatar.textContent = initials;
    portalStudentName.textContent = user.name;
    portalCollegeName.textContent = user.college;
    portalDepartment.textContent = user.department;
    portalYear.textContent = user.year;
    portalEmail.textContent = user.email;
    portalPhone.textContent = user.phone;

    // Populate Career form inputs
    const career = user.career || {};

    githubLink.value = career.github || '';
    linkedinLink.value = career.linkedin || '';
    leetcodeLink.value = career.leetcode || '';
    portfolioLink.value = career.portfolio || '';

    // Handle resume state
    if (career.resume && career.resume.name) {
      temporaryUploadedResume = career.resume;
      displayAttachedFile(career.resume.name, career.resume.size, career.resume.type);
    } else {
      temporaryUploadedResume = null;
      hideAttachedFile();
    }

    // Sync recruiter live card
    updateRecruiterCard(user);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function displayAttachedFile(name, size, type) {
    fileNameDisplay.textContent = name;
    fileSizeDisplay.textContent = size;
    fileTypeIcon.textContent = name.toLowerCase().endsWith('.docx') || name.toLowerCase().endsWith('.doc') ? 'DOC' : 'PDF';
    attachedFileInfo.classList.remove('hidden');
    dropZonePrompt.classList.add('hidden');
  }

  function hideAttachedFile() {
    attachedFileInfo.classList.add('hidden');
    dropZonePrompt.classList.remove('hidden');
    resumeFileInput.value = '';
  }

  // ==========================================================================
  // Resume File Upload & Browser Handling
  // ==========================================================================
  browseFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resumeFileInput.click();
  });

  resumeDropZone.addEventListener('click', () => {
    resumeFileInput.click();
  });

  // Drag and Drop
  ['dragenter', 'dragover'].forEach(eventName => {
    resumeDropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      resumeDropZone.classList.add('drag-active');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    resumeDropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      resumeDropZone.classList.remove('drag-active');
    }, false);
  });

  resumeDropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      processSelectedFile(files[0]);
    }
  });

  resumeFileInput.addEventListener('change', function () {
    if (this.files && this.files.length > 0) {
      processSelectedFile(this.files[0]);
    }
  });

  function processSelectedFile(file) {
    clearError('resumeError');

    // Validation
    const validExtensions = ['.pdf', '.doc', '.docx'];
    const fileName = file.name;
    const fileExt = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();

    if (!validExtensions.includes(fileExt)) {
      setError('resumeError', 'Invalid file type. Only PDF, DOC, and DOCX files are allowed.');
      showToast('Unsupported File Type', 'Please upload a PDF or Word document', 'error');
      return;
    }

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      setError('resumeError', 'File exceeds 10MB limit. Please upload a smaller file.');
      return;
    }

    // Read file via FileReader
    const reader = new FileReader();
    reader.onload = function (e) {
      temporaryUploadedResume = {
        name: file.name,
        size: formatFileSize(file.size),
        type: file.type || 'application/pdf',
        dataUrl: e.target.result
      };

      displayAttachedFile(temporaryUploadedResume.name, temporaryUploadedResume.size, temporaryUploadedResume.type);
      showToast('Resume File Selected', `Attached: ${file.name} (${formatFileSize(file.size)})`, 'success');
    };

    reader.readAsDataURL(file);
  }

  // Preview / Inspect Resume
  previewResumeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!temporaryUploadedResume) return;

    if (temporaryUploadedResume.dataUrl) {
      const win = window.open();
      win.document.write(`<iframe src="${temporaryUploadedResume.dataUrl}" frameborder="0" style="border:0; top:0px; left:0px; bottom:0px; right:0px; width:100%; height:100%;" allowfullscreen></iframe>`);
    } else {
      showToast('Resume Preview', `Inspecting attached file: ${temporaryUploadedResume.name}`, 'info');
    }
  });

  // Remove Resume
  removeResumeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    temporaryUploadedResume = null;
    hideAttachedFile();
    showToast('Resume Removed', 'You can browse and select another file', 'info');
  });

  // Test Link in New Tab buttons
  document.querySelectorAll('.btn-input-test').forEach(btn => {
    btn.addEventListener('click', function () {
      const targetInputId = this.getAttribute('data-test');
      const input = document.getElementById(targetInputId);
      const url = input.value.trim();

      if (!url) {
        showToast('Empty Link', 'Please enter a URL first to test', 'warning');
        return;
      }

      if (!isValidUrl(url)) {
        showToast('Invalid URL', 'Please enter a valid link starting with https://', 'error');
        return;
      }

      window.open(url, '_blank', 'noopener,noreferrer');
    });
  });

  // ==========================================================================
  // Save & Submit Career Details
  // ==========================================================================
  careerProfileForm.addEventListener('submit', function (e) {
    e.preventDefault();

    clearError('resumeError');
    clearError('githubError');
    clearError('linkedinError');
    clearError('leetcodeError');
    clearError('portfolioError');

    const currentUser = getCurrentUser();
    if (!currentUser) {
      showToast('Session Expired', 'Please sign in again', 'error');
      navLogoutBtn.click();
      return;
    }

    const github = githubLink.value.trim();
    const linkedin = linkedinLink.value.trim();
    const leetcode = leetcodeLink.value.trim();
    const portfolio = portfolioLink.value.trim();

    let hasError = false;

    // Resume check
    if (!temporaryUploadedResume) {
      setError('resumeError', 'Please browse and upload your resume / CV file');
      hasError = true;
    }

    // Links format checks
    if (!github) {
      setError('githubError', 'GitHub profile link is required');
      hasError = true;
    } else if (!isValidUrl(github)) {
      setError('githubError', 'Please enter a valid URL (e.g. https://github.com/username)');
      hasError = true;
    }

    if (!linkedin) {
      setError('linkedinError', 'LinkedIn profile link is required');
      hasError = true;
    } else if (!isValidUrl(linkedin)) {
      setError('linkedinError', 'Please enter a valid URL (e.g. https://linkedin.com/in/username)');
      hasError = true;
    }

    if (!leetcode) {
      setError('leetcodeError', 'LeetCode profile link is required');
      hasError = true;
    } else if (!isValidUrl(leetcode)) {
      setError('leetcodeError', 'Please enter a valid URL (e.g. https://leetcode.com/username)');
      hasError = true;
    }

    if (!portfolio) {
      setError('portfolioError', 'Personal portfolio link is required');
      hasError = true;
    } else if (!isValidUrl(portfolio)) {
      setError('portfolioError', 'Please enter a valid URL (e.g. https://yourportfolio.dev)');
      hasError = true;
    }

    if (hasError) {
      showToast('Incomplete Form', 'Please fix highlighted errors before saving', 'warning');
      return;
    }

    // Save details to student record
    currentUser.career = {
      resume: temporaryUploadedResume,
      github,
      linkedin,
      leetcode,
      portfolio
    };

    // Update in users storage
    const users = getUsers();
    const idx = users.findIndex(u => u.email.toLowerCase() === currentUser.email.toLowerCase());
    if (idx !== -1) {
      users[idx] = currentUser;
      saveUsers(users);
    }
    setCurrentUser(currentUser);

    // Update Showcase Card
    updateRecruiterCard(currentUser);

    showToast('Career Details Saved! 🎉', 'Your resume and coding profiles are now live on your portfolio card.', 'success', 5000);
  });

  // ==========================================================================
  // Update Live Recruiter Showcase Card
  // ==========================================================================
  function updateRecruiterCard(user) {
    showcaseAvatar.textContent = getInitials(user.name);
    showcaseName.textContent = user.name;
    showcaseCollege.textContent = user.college;
    showcaseDept.textContent = `${user.department} • ${user.year}`;

    const career = user.career || {};

    // Resume info
    if (career.resume && career.resume.name) {
      showcaseResumeName.textContent = `${career.resume.name} (${career.resume.size})`;
      downloadResumeAction.disabled = false;
      downloadResumeAction.onclick = () => {
        if (career.resume.dataUrl) {
          const a = document.createElement('a');
          a.href = career.resume.dataUrl;
          a.download = career.resume.name;
          document.body.appendChild(a);
          a.click();
          a.remove();
        } else {
          showToast('Resume Download', `Initiating download of ${career.resume.name}`, 'info');
        }
      };
    } else {
      showcaseResumeName.textContent = 'No resume attached yet';
      downloadResumeAction.disabled = true;
      downloadResumeAction.onclick = null;
    }

    // GitHub Link
    configureShowcaseLink(showcaseGithubLink, career.github, 'github.com');
    // LinkedIn Link
    configureShowcaseLink(showcaseLinkedinLink, career.linkedin, 'linkedin.com');
    // LeetCode Link
    configureShowcaseLink(showcaseLeetcodeLink, career.leetcode, 'leetcode.com');
    // Portfolio Link
    configureShowcaseLink(showcasePortfolioLink, career.portfolio, 'View Portfolio');
  }

  function configureShowcaseLink(element, url, placeholder) {
    if (url && isValidUrl(url)) {
      element.href = url;
      element.classList.remove('disabled');
      try {
        const parsed = new URL(url);
        element.querySelector('span').textContent = parsed.hostname.replace('www.', '') + (parsed.pathname !== '/' ? parsed.pathname.substring(0, 15) : '');
      } catch (_) {
        element.querySelector('span').textContent = placeholder;
      }
    } else {
      element.href = '#';
      element.classList.add('disabled');
      element.querySelector('span').textContent = 'Not set';
    }
  }

  // ==========================================================================
  // Sign Out Handler
  // ==========================================================================
  navLogoutBtn.addEventListener('click', () => {
    setCurrentUser(null);
    portalView.classList.add('hidden');
    navLogoutBtn.classList.add('hidden');
    authView.classList.remove('hidden');

    // Restore remembered email if present
    const remembered = localStorage.getItem(REMEMBER_KEY);
    if (remembered) {
      loginEmail.value = remembered;
      rememberMe.checked = true;
    } else {
      loginEmail.value = '';
      rememberMe.checked = false;
    }
    loginPassword.value = '';

    showTab('signin');
    showToast('Signed Out', 'You have been securely signed out', 'info');
  });

  // ==========================================================================
  // App Initialization
  // ==========================================================================
  function initApp() {
    initDatabase();

    // Check if user is remembered
    const remembered = localStorage.getItem(REMEMBER_KEY);
    if (remembered) {
      loginEmail.value = remembered;
      rememberMe.checked = true;
    }

    // Check active session
    const activeUser = getCurrentUser();
    if (activeUser) {
      renderPortal(activeUser);
    } else {
      showTab('signin');
    }
  }

  // Run on load
  initApp();
})();
