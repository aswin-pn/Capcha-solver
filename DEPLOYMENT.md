# CAPTCHA Solver Deployment Guide

## Overview
This guide will help you deploy the CAPTCHA solver service to your domain `sellmyagent.com` using Render.

## Files Created for Deployment

1. **`app.py`** - Main Flask application for the CAPTCHA solver
2. **`requirements.txt`** - Python dependencies
3. **`Procfile`** - Tells Render how to run the app
4. **`runtime.txt`** - Specifies Python version
5. **`DEPLOYMENT.md`** - This deployment guide

## Step 1: GitHub Repository Setup

1. Create a new GitHub repository
2. Upload these files to your repository:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`

## Step 2: Render Deployment

1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `captcha-solver` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free (or paid if you need more resources)

## Step 3: Domain Configuration

1. In your Render dashboard, go to your web service
2. Click on "Settings" tab
3. Scroll down to "Custom Domains"
4. Add your domain: `sellmyagent.com`
5. Render will provide you with DNS records to configure

## Step 4: DNS Configuration in GoDaddy

1. Log into your GoDaddy account
2. Go to your domain `sellmyagent.com`
3. Click "DNS" or "Manage DNS"
4. Add these records (Render will provide the exact values):

   **Type A Record:**
   - Name: `@` (or leave blank)
   - Value: [Render's IP address]
   - TTL: 600

   **Type CNAME Record:**
   - Name: `www`
   - Value: [Your Render service URL]
   - TTL: 600

## Step 5: SSL Certificate

1. Render will automatically provision an SSL certificate
2. This may take a few minutes to activate
3. Your site will be accessible at `https://sellmyagent.com`

## Step 6: Testing

1. Once deployed, visit `https://sellmyagent.com`
2. You should see the CAPTCHA solver interface
3. Test the health endpoint: `https://sellmyagent.com/health`

## Step 7: Update LinkedIn Script

The LinkedIn script (`linkedin_captcha_solver.py`) has been updated to use:
- `https://sellmyagent.com/solve` for sending CAPTCHA images
- `https://sellmyagent.com/answer` for polling answers

## Troubleshooting

1. **Build fails**: Check that all files are in the repository
2. **Domain not working**: Verify DNS records are correct
3. **SSL issues**: Wait a few minutes for certificate provisioning
4. **Service not starting**: Check the logs in Render dashboard

## Security Notes

- The service stores CAPTCHA images in memory (not persistent)
- Consider adding authentication if needed
- Monitor usage to avoid abuse

## Support

If you encounter issues:
1. Check Render logs in the dashboard
2. Verify DNS propagation using tools like `nslookup`
3. Test the health endpoint to ensure the service is running 