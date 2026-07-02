import re
import os

path = r'c:\Users\pc\OneDrive\Desktop\nutritrack\frontend\index.html'

with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

s = html.find('<div id="authSection">')
e = html.find('<!-- ONBOARDING SECTION')

if s != -1 and e != -1:
    new_auth = """<div id="authSection" style="display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 2rem;">
    <div class="auth-wrapper" style="width: 100%; max-width: 900px;">
      <div class="auth-card" style="display: flex; flex-direction: row; align-items: stretch; padding: 0; overflow: hidden; background: rgba(18,17,15,0.7); backdrop-filter: blur(16px); border-radius: 24px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 24px 64px rgba(0,0,0,0.4);">
        
        <!-- Left Side: Email/Password -->
        <div class="auth-left" style="flex: 1; padding: 3.5rem; display: flex; flex-direction: column; justify-content: center; position: relative;">
          <div class="auth-logo" style="margin-bottom: 2rem; text-align: left;">
            <div class="logo-mark" style="width: auto; height: auto; background: transparent; border: none; box-shadow: none; margin-bottom: 0; display: inline-flex;">
              <img src="logo-auth.png" alt="Auth Logo" style="width: 220px; height: auto;" />
            </div>
            <p style="color: rgba(184,201,186,0.6); margin-top: 0.8rem; font-size: 0.95rem;">Sign in to continue your journey</p>
          </div>

          <div id="authError" class="auth-error" style="display: none; margin-bottom: 1rem;"></div>
          <div id="authSuccess" class="auth-error" style="display: none; margin-bottom: 1rem; background: rgba(62,207,142,0.1); color: #3ecf8e; border-color: rgba(62,207,142,0.3);"></div>

          <div id="loginForm">
            <div class="field-group">
              <label for="loginEmail">Email Address</label>
              <input type="email" id="loginEmail" placeholder="you@example.com">
            </div>
            <div class="field-group" style="position: relative;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <label for="loginPassword" style="margin-bottom: 0;">Password</label>
                <a href="#" onclick="handleForgotPassword()" style="font-size: 0.8rem; color: #3ecf8e; text-decoration: none; transition: opacity 0.2s;">Forgot password?</a>
              </div>
              <input type="password" id="loginPassword" placeholder="••••••••">
            </div>
            <button type="button" class="submit-btn" onclick="handleEmailLogin()" style="margin-top: 0.5rem; margin-bottom: 1.5rem; font-size: 1rem; padding: 0.9rem;">Sign In / Register &rarr;</button>
            <p style="font-size: 0.8rem; color: rgba(184,201,186,0.5); text-align: center; line-height: 1.4;">If you don't have an account, one will be created automatically.</p>
          </div>
        </div>

        <!-- Divider -->
        <div class="auth-divider" style="width: 1px; background: rgba(255,255,255,0.08); margin: 0;"></div>

        <!-- Right Side: Google OAuth -->
        <div class="auth-right" style="flex: 1; padding: 3.5rem; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; background: rgba(0,0,0,0.15);">
          <div style="font-size: 3rem; margin-bottom: 1.5rem;">&#9889;</div>
          <h3 style="margin-bottom: 1rem; font-weight: 600; font-size: 1.5rem; color: #fff;">Fast & Secure</h3>
          <p style="color: rgba(184,201,186,0.7); font-size: 0.95rem; line-height: 1.5; margin-bottom: 2.5rem; max-width: 280px;">Log in instantly with your Google account. No passwords to remember.</p>
          
          <button type="button" class="submit-btn" onclick="handleGoogleLogin()" style="background: #ffffff; color: #000000; font-weight: 600; font-size: 1rem; display: flex; align-items: center; justify-content: center; gap: 12px; border: none; padding: 0.9rem 1.5rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 100%; max-width: 280px; transition: transform 0.2s, box-shadow 0.2s; cursor: pointer;">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Sign in with Google
          </button>
        </div>
      </div>
    </div>
  </div>
  
  """
    
    html = html[:s] + new_auth + html[e:]
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print("index.html patched!")
else:
    print("Could not find authSection bounds.")
