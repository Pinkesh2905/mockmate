import json
import time
import base64
import logging
from io import BytesIO
import tempfile
import re
import os
import uuid
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

# Resume parsing libs
import pdfplumber
import docx2txt

# AI providers
import openai
import google.generativeai as genai
from google.genai import types

# gTTS for text-to-speech
from gtts import gTTS

import logging
logger = logging.getLogger(__name__)

from .models import MockInterviewSession, InterviewTurn
from .forms import InterviewSetupForm


# -------------------------
# Role check helpers
# -------------------------
def is_student(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'STUDENT'

def is_tutor(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'TUTOR' and user.profile.is_approved_tutor

def is_admin(user):
    return user.is_authenticated and user.is_superuser

# -------------------------
# AI Provider Setup
# -------------------------
AI_PROVIDER = getattr(settings, "AI_PROVIDER", "gemini").lower()
GEMINI_API_KEY = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", "")

if AI_PROVIDER == "openai" and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
elif AI_PROVIDER == "gemini" and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("No valid AI provider key configured. AI features will not work.")

# -------------------------
# gTTS Function
# -------------------------
def synthesize_speech_gtts(text, filename):
    """Convert text to speech using gTTS with Indian English accent and save MP3."""
    try:
        # Use Indian English voice
        tts = gTTS(
            text=text,
            lang='en',       # English
            tld='co.in',     # Indian accent
            slow=False       # Fast pace
        )

        # Create media/audio directory if not exists
        audio_dir = os.path.join(settings.MEDIA_ROOT, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(audio_dir, filename)
        tts.save(file_path)

        # Optional: Post-process to increase playback speed slightly
        # Requires pydub (pip install pydub)
        try:
            from pydub import AudioSegment
            sound = AudioSegment.from_file(file_path)
            faster_sound = sound.speedup(playback_speed=1.25)  # 25% faster
            faster_sound.export(file_path, format="mp3")
        except ImportError:
            logger.warning("pydub not installed, skipping speed boost")

        # Return public URL
        return settings.MEDIA_URL + "audio/" + filename

    except Exception as e:
        logger.error(f"gTTS failed: {e}")
        return None



# -------------------------
# Enhanced AI Call Function with gTTS
# -------------------------
def call_ai_model(prompt, model_type="text", max_tokens=150, temperature=0.7):
    """
    Calls the configured AI model to generate text or speech.
    Supports: "text", "tts", "gtts".
    """

    try:
        if AI_PROVIDER == "gemini":
            if model_type == "tts":
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash-preview-tts")
                    content_parts = [{'text': prompt}]
                    generation_config = {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {
                                    "voice_name": "Aoede"
                                }
                            }
                        }
                    }
                    response = model.generate_content(content_parts, generation_config=generation_config)
                    if response.candidates and len(response.candidates) > 0:
                        part = response.candidates[0].content.parts[0]
                        if hasattr(part, 'inline_data') and part.inline_data:
                            audio_base64 = part.inline_data.data
                            mime = part.inline_data.mime_type
                            return {"audio_base64": audio_base64, "mime": mime or "audio/wav"}
                    return {"audio_base64": "", "mime": ""}
                except Exception as tts_error:
                    logger.error(f"Gemini TTS failed: {tts_error}")
                    return {"audio_base64": "", "mime": ""}

            elif model_type == "gtts":
                try:
                    from gtts import gTTS
                    import os, time, uuid
                    from django.conf import settings

                    audio_filename = f"interview_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp3"
                    audio_dir = os.path.join(settings.MEDIA_ROOT, "audio")
                    os.makedirs(audio_dir, exist_ok=True)
                    file_path = os.path.join(audio_dir, audio_filename)

                    # Indian accent, faster speech
                    tts = gTTS(text=prompt, lang='en', slow=False, tld='co.in')
                    tts.save(file_path)

                    # Try speeding up with pydub (optional)
                    try:
                        from pydub import AudioSegment
                        sound = AudioSegment.from_file(file_path)
                        faster = sound.speedup(playback_speed=1.15)
                        faster.export(file_path, format="mp3")
                        logger.info("Applied 15% speed boost to audio")
                    except Exception as speed_err:
                        logger.warning(f"Skipping pydub speed boost: {speed_err}")

                    return {"audio_url": settings.MEDIA_URL + "audio/" + audio_filename, "mime": "audio/mpeg"}

                except Exception as e:
                    logger.error(f"gTTS failed: {e}")
                    return {"audio_url": None, "mime": ""}

            else:
                model = genai.GenerativeModel("gemini-1.5-flash")
                generation_config = {
                    'temperature': temperature,
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': max_tokens,
                }
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text.strip()

        elif AI_PROVIDER == "openai":
            if model_type == "tts":
                try:
                    response = openai.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=prompt[:4000],
                        speed=1.15,  # slightly faster than default
                        response_format="mp3"
                    )
                    audio_bytes = response.content
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                    return {"audio_base64": audio_base64, "mime": "audio/mpeg"}
                except Exception as tts_error:
                    logger.error(f"OpenAI TTS failed: {tts_error}")
                    return {"audio_base64": "", "mime": ""}

            elif model_type == "gtts":
                try:
                    from gtts import gTTS
                    import os, time, uuid
                    from django.conf import settings

                    audio_filename = f"interview_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp3"
                    audio_dir = os.path.join(settings.MEDIA_ROOT, "audio")
                    os.makedirs(audio_dir, exist_ok=True)
                    file_path = os.path.join(audio_dir, audio_filename)

                    tts = gTTS(text=prompt, lang='en', slow=False, tld='co.in')
                    tts.save(file_path)

                    try:
                        from pydub import AudioSegment
                        sound = AudioSegment.from_file(file_path)
                        faster = sound.speedup(playback_speed=1.15)
                        faster.export(file_path, format="mp3")
                        logger.info("Applied 15% speed boost to audio")
                    except Exception as speed_err:
                        logger.warning(f"Skipping pydub speed boost: {speed_err}")

                    return {"audio_url": settings.MEDIA_URL + "audio/" + audio_filename, "mime": "audio/mpeg"}

                except Exception as e:
                    logger.error(f"gTTS failed: {e}")
                    return {"audio_url": None, "mime": ""}

            else:
                resp = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return resp.choices[0].message.content.strip()

        else:
            raise RuntimeError("Invalid AI provider configured.")

    except Exception as e:
        logger.exception(f"AI model call failed (type={model_type}): {e}")
        if model_type in ["tts", "gtts"]:
            return {"audio_base64": "", "mime": "", "audio_url": None}
        else:
            return ""

# -------------------------
# Enhanced Resume parsing
# -------------------------
def extract_text_from_pdf(file_obj):
    text_parts = []
    try:
        file_bytes = file_obj.read()
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        logger.exception("Failed to extract PDF text: %s", e)
    return "\n".join(text_parts).strip()

def extract_text_from_docx(file_obj):
    try:
        file_bytes = file_obj.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tf:
            tf.write(file_bytes)
            temp_path = tf.name
        return docx2txt.process(temp_path).strip()
    except Exception as e:
        logger.exception("Failed to extract DOCX text: %s", e)
        return ""

def parse_resume_file(file_obj, filename=None):
    if not file_obj:
        return ""
    fname = (filename or getattr(file_obj, 'name', '')).lower()
    if fname.endswith('.pdf'):
        return extract_text_from_pdf(file_obj)
    if fname.endswith(('.docx', '.doc')):
        return extract_text_from_docx(file_obj)
    try:
        return file_obj.read().decode('utf-8', errors='ignore')
    except Exception:
        return ""

def extract_structured_from_resume_text(resume_text):
    prompt = (
        "You are an expert resume parsing assistant. Extract comprehensive information from this resume. "
        "Analyze the content thoroughly and return ONLY a valid JSON object with these exact keys:\n"
        "- job_role: Primary target job title/role\n"
        "- skills: Array of technical and soft skills (deduplicated)\n"
        "- experience_years: Estimated years of experience\n"
        "- education: Highest education level\n"
        "- summary: Professional summary (1-2 sentences)\n"
        "- key_achievements: Top 3 achievements/accomplishments\n"
        "- industries: Relevant industry experience\n\n"
        f"Resume text:\n{resume_text[:25000]}"
    )
    ai_output = call_ai_model(prompt, model_type="text", max_tokens=800)
    try:
        json_patterns = [
            r'\{[\s\S]*\}',
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```'
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, ai_output)
            if match:
                json_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
                parsed = json.loads(json_str)
                return {
                    "job_role": parsed.get("job_role", ""),
                    "skills": parsed.get("skills", []),
                    "experience_years": parsed.get("experience_years", 0),
                    "education": parsed.get("education", ""),
                    "summary": parsed.get("summary", ""),
                    "key_achievements": parsed.get("key_achievements", []),
                    "industries": parsed.get("industries", []),
                    "raw": ai_output
                }
    except Exception as e:
        logger.warning(f"Failed to parse AI resume analysis: {e}")
    
    return {
        "job_role": "", "skills": [], "experience_years": 0, 
        "education": "", "summary": "", "key_achievements": [], 
        "industries": [], "raw": ai_output
    }

# -------------------------
# Enhanced Interview Logic with Friendlier AI Interviewer
# -------------------------
def generate_friendly_interview_prompt(session, turn_count=0, conversation_context="", user_response=""):
    """Generate a short, friendly, and professional HR interview prompt."""
    
    if turn_count == 0:
        return f"""
        You are Sarah, a warm, encouraging, and professional HR interviewer at a modern tech company. 
        You are interviewing for a {session.job_role} position.

        Key skills to assess: {session.key_skills}

        Start with a short, friendly welcome (1–2 sentences max). 
        Make the candidate feel comfortable but get to the first question quickly.
        Keep your questions concise, conversational, and professional.
        Avoid long speeches — speak like a real HR interviewer.

        Example start:
        "Hi! I’m Sarah from the HR team. I’m excited to chat with you about the {session.job_role} role. 
        To begin, could you give me a brief intro about yourself and what drew you to this position?"

        Keep tone warm, natural, and human.
        """

    # Stage guidance – fast-paced, short, and targeted
    if turn_count <= 2:
        stage_guidance = """
        Focus: Quick background and comfort-building.
        Ask short, open-ended questions about their experience or background.
        Example: "Could you share one key project or achievement you’re proud of?"
        """
    elif turn_count <= 5:
        stage_guidance = f"""
        Focus: Core technical/role-specific skills for {session.job_role}.
        Ask 1 clear technical or problem-solving question at a time.
        Example: "What’s one challenge you’ve solved using {session.key_skills.split(',')[0].strip()}?"
        """
    elif turn_count <= 8:
        stage_guidance = """
        Focus: Behavioral/situational.
        Ask for 1 short example using STAR method without explaining STAR.
        Example: "Can you recall a time you had to resolve a tough issue under pressure?"
        """
    else:
        stage_guidance = """
        Focus: Wrap-up quickly.
        Ask if they have questions or want to share final thoughts.
        If ending, prefix with "INTERVIEW_COMPLETE" and give a short, warm closing.
        """

    return f"""
    You are Sarah, the HR interviewer.
    Role: {session.job_role}
    Key skills: {session.key_skills}
    Question number: {turn_count + 1}

    {stage_guidance}

    Conversation so far:
    {conversation_context}

    Candidate’s last answer: "{user_response}"

    Style guidelines:
    - Keep your response under 2–3 sentences.
    - Acknowledge their answer briefly ("That’s great", "Interesting point").
    - Immediately ask your next question — no long stories.
    - Remain friendly, approachable, and professional.
    - Avoid technical jargon unless needed.
    - Encourage them subtly: "I’d love to hear more", "That’s a great example".
    
    Now, generate Sarah’s next short, friendly, and professional question:
    """

def analyze_interview_performance(session):
    """Enhanced performance analysis with more detailed feedback."""
    turns = session.turns.all().order_by('turn_number')
    conversation = []
    
    for turn in turns:
        if turn.ai_question:
            conversation.append(f"INTERVIEWER: {turn.ai_question}")
        if turn.user_answer:
            conversation.append(f"CANDIDATE: {turn.user_answer}")
    
    analysis_prompt = f"""
    Analyze this mock interview for a {session.job_role} position with empathy and constructive feedback.
    
    Key skills assessed: {session.key_skills}
    Total questions: {len(turns)}
    
    Conversation:
    {chr(10).join(conversation[-20:])}
    
    Provide encouraging yet honest analysis in JSON format:
    {{
        "overall_score": 85,
        "strengths": ["specific positive aspects"],
        "areas_for_improvement": ["constructive suggestions"],
        "technical_assessment": "Detailed technical evaluation",
        "communication_score": 90,
        "confidence_level": "Growing/Good/Excellent",
        "body_language_notes": "Based on responses, inferred confidence level",
        "recommendations": ["specific actionable advice"],
        "encouragement_note": "Personal encouraging message",
        "next_steps": ["concrete steps for improvement"]
    }}
    
    Be encouraging, specific, and actionable in your feedback.
    """
    
    return call_ai_model(analysis_prompt, model_type="text", max_tokens=1200)

# -------------------------
# Enhanced Views
# -------------------------

@csrf_exempt
def start_mock_interview(request):
    """Start the mock interview session - new endpoint."""
    return render(request, "mock_interview/start.html")

@login_required
@user_passes_test(is_student, login_url='/login/')
def interview_setup(request):
    prefill = {}
    if request.method == 'POST':
        form = InterviewSetupForm(request.POST, request.FILES)
        resume_file = request.FILES.get('resume_file')
        if resume_file:
            try:
                resume_text = parse_resume_file(resume_file, filename=resume_file.name)
                if resume_text:
                    parsed = extract_structured_from_resume_text(resume_text)
                    prefill.update({
                        'job_role': parsed.get('job_role', ''),
                        'key_skills': ", ".join(parsed.get('skills', [])),
                    })
                    request.session['resume_analysis'] = parsed
                else:
                    messages.warning(request, "Could not extract text from resume.")
            except Exception as e:
                logger.exception("Error parsing resume: %s", e)
                messages.error(request, "Failed to parse resume.")
            post_data = request.POST.copy()
            for k, v in prefill.items():
                if not post_data.get(k):
                    post_data[k] = v
            form = InterviewSetupForm(post_data, request.FILES)

        if form.is_valid():
            session = form.save(commit=False)
            session.user = request.user
            session.status = 'STARTED'
            session.start_time = timezone.now()
            resume_data = request.session.get('resume_analysis', {})
            if resume_data:
                session.additional_data = json.dumps(resume_data)
            session.save()
            form.save_m2m()
            return redirect('mock_interview:main_interview', session_id=session.id)
    else:
        form = InterviewSetupForm()
    return render(request, 'mock_interview/interview_setup.html', {'form': form})

@login_required
@user_passes_test(is_student, login_url='/login/')
def main_interview(request, session_id):
    session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
    if session.status in ['COMPLETED', 'REVIEWED']:
        return redirect('mock_interview:review_interview', session_id=session.id)
    if session.status != 'STARTED':
        session.status = 'STARTED'
        session.save(update_fields=['status'])
    
    initial_chat_history = []
    turns = session.turns.all().order_by('turn_number')
    
    for turn in turns:
        if turn.ai_question:
            initial_chat_history.append({
                'role': 'model', 
                'parts': [{'text': turn.ai_question}],
                'timestamp': turn.created_at.isoformat() if hasattr(turn, 'created_at') else None,
                'turn_number': turn.turn_number
            })
        if turn.user_answer:
            initial_chat_history.append({
                'role': 'user', 
                'parts': [{'text': turn.user_answer}],
                'timestamp': turn.created_at.isoformat() if hasattr(turn, 'created_at') else None,
                'turn_number': turn.turn_number
            })
    
    total_turns = turns.count()
    estimated_duration = (timezone.now() - session.start_time).total_seconds() / 60 if session.start_time else 0
    
    return render(request, 'mock_interview/main_interview.html', {
        'session_id': session.id,
        'job_role': session.job_role,
        'key_skills': session.key_skills,
        'initial_chat_history_json': json.dumps(initial_chat_history),
        'interview_progress': {
            'total_questions': total_turns,
            'estimated_duration': round(estimated_duration, 1),
            'target_duration': 20
        }
    })

@csrf_exempt
def interact_with_ai(request, interview_id):
    """Enhanced AI interaction endpoint with gTTS integration."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=400)
    
    try:
        # Get user input
        user_input = request.POST.get("userResponse", "").strip()
        
        # For this endpoint, create a simple interview context
        # You might want to integrate this with your session model
        interview_prompt = f"""
        You are Sarah, a warm and friendly HR interviewer. 
        
        The candidate just said: "{user_input}"
        
        Respond naturally and encouragingly as a professional interviewer would.
        Keep your response conversational, warm, and under 200 words.
        Ask a relevant follow-up question or move to the next interview topic.
        
        Be encouraging and show genuine interest in their responses.
        """
        
        # Generate AI text response
        if AI_PROVIDER == "gemini":
            model = genai.GenerativeModel("gemini-1.5-flash")
            gemini_response = model.generate_content(interview_prompt)
            ai_text = gemini_response.text.strip()
        else:
            ai_text = call_ai_model(interview_prompt, model_type="text", max_tokens=300, temperature=0.8)
        
        # Generate audio using gTTS
        ai_audio_url = None
        try:
            audio_result = call_ai_model(ai_text, model_type="gtts")
            if audio_result.get("audio_url"):
                ai_audio_url = audio_result["audio_url"]
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            ai_audio_url = None
        
        return JsonResponse({
            "success": True,
            "ai_response_text": ai_text,
            "ai_audio_url": ai_audio_url,
            "interview_complete": False,
            "debug_info": {
                "audio_generated": bool(ai_audio_url),
                "text_length": len(ai_text),
                "tts_method": "gtts"
            }
        })
        
    except Exception as e:
        logger.exception("AI interaction failed")
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@login_required
@user_passes_test(is_student, login_url='/login/')
@csrf_exempt
def ai_interaction_api(request, session_id):
    """Enhanced main AI interaction endpoint with gTTS integration."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
    session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
    
    try:
        payload = json.loads(request.body)
        user_response_text = payload.get('user_response', '').strip()
        chat_history = payload.get('chat_history', [])
        request_type = payload.get('request_type', 'normal')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    current_turn_count = session.turns.count()
    interview_duration = (timezone.now() - session.start_time).total_seconds() / 60
    
    # Build conversation context for better continuity
    conversation_context = []
    for msg in chat_history[-6:]:  # Last 6 messages for context
        role = "SARAH" if msg.get('role') == 'model' else "CANDIDATE"
        text = msg.get('parts', [{}])[0].get('text', '')
        conversation_context.append(f"{role}: {text}")
    
    context_str = "\n".join(conversation_context)
    
    # Generate friendly interview prompt
    ai_prompt = generate_friendly_interview_prompt(
        session, 
        current_turn_count, 
        context_str, 
        user_response_text
    )
    
    # Add interview progress context
    ai_prompt += f"""
    
    Interview Progress Context:
    - Current question: {current_turn_count + 1}
    - Duration so far: {interview_duration:.1f} minutes
    - Target duration: 15-20 minutes
    
    If this is question 10+ or duration > 18 minutes: Consider wrapping up warmly.
    When ready to end, start your response with "INTERVIEW_COMPLETE" followed by warm closing remarks.
    
    Remember: You're Sarah - warm, encouraging, and genuinely interested in this candidate!
    """

    # Call AI model for response
    ai_response_text = call_ai_model(ai_prompt, model_type="text", max_tokens=350, temperature=0.8)
    
    # Check if interview should complete
    is_complete = False
    if (ai_response_text.startswith("INTERVIEW_COMPLETE") or 
        current_turn_count >= 12 or 
        interview_duration > 22):
        is_complete = True
        if ai_response_text.startswith("INTERVIEW_COMPLETE"):
            ai_response_text = ai_response_text.replace("INTERVIEW_COMPLETE", "").strip()
        else:
            ai_response_text += " This has been such a wonderful conversation! Thank you so much for your time and thoughtful answers today. You'll receive detailed feedback very soon. Have a great day!"

    # Generate audio with gTTS
    audio_data_url = None
    
    if ai_response_text and len(ai_response_text.strip()) > 0:
        clean_text = re.sub(r'[^\w\s.,!?-]', '', ai_response_text).strip()
        
        if len(clean_text) > 10:
            logger.info(f"Generating TTS for: {clean_text[:100]}...")
            
            # Try gTTS first
            try:
                audio_result = call_ai_model(clean_text, model_type="gtts")
                if audio_result.get("audio_url"):
                    audio_data_url = audio_result["audio_url"]
                    logger.info("gTTS successful")
                else:
                    raise Exception("gTTS returned no URL")
            except Exception as e:
                logger.warning(f"gTTS failed, trying fallback: {e}")
                # Fallback to other TTS methods
                try:
                    tts_result = call_ai_model(clean_text, model_type="tts")
                    if tts_result.get("audio_base64") and len(tts_result.get("audio_base64")) > 0:
                        audio_data_url = f"data:{tts_result.get('mime', 'audio/wav')};base64,{tts_result.get('audio_base64')}"
                        logger.info("Fallback TTS successful")
                except Exception as fallback_error:
                    logger.error(f"All TTS methods failed: {fallback_error}")

    # Save interaction to database
    InterviewTurn.objects.create(
        session=session,
        turn_number=current_turn_count + 1,
        ai_question=ai_response_text,
        user_answer=user_response_text,
        ai_internal_analysis=f"Turn {current_turn_count + 1}: Duration {interview_duration:.1f}min, Audio: {'Yes' if audio_data_url else 'No'}, gTTS: Active"
    )

    # Complete interview if needed
    if is_complete:
        session.status = 'COMPLETED'
        session.end_time = timezone.now()
        
        try:
            performance_analysis = analyze_interview_performance(session)
            session.ai_feedback = performance_analysis
        except Exception as e:
            logger.warning(f"Failed to generate performance analysis: {e}")
        
        session.save()

    # Enhanced response data
    response_data = {
        "success": True,
        "ai_response_text": ai_response_text,
        "ai_audio_url": audio_data_url,
        "interview_complete": is_complete,
        "interview_progress": {
            "current_question": current_turn_count + 1,
            "duration_minutes": round(interview_duration, 1),
            "estimated_remaining": max(0, 20 - interview_duration)
        },
        "interviewer_mood": "friendly_and_encouraging",
        "debug_info": {
            "audio_generated": bool(audio_data_url),
            "audio_method": "gtts" if audio_data_url and not audio_data_url.startswith("data:") else "fallback",
            "text_length": len(ai_response_text),
            "turn_count": current_turn_count + 1
        }
    }
    
    logger.info(f"AI response sent: audio={'present' if audio_data_url else 'missing'}, method={'gtts' if audio_data_url and not audio_data_url.startswith('data:') else 'fallback'}")
    return JsonResponse(response_data)

@login_required
@user_passes_test(is_student, login_url='/login/')
def my_mock_interviews(request):
    sessions = MockInterviewSession.objects.filter(user=request.user).order_by('-start_time')
    
    # Add enhanced performance metrics to each session
    for session in sessions:
        if hasattr(session, 'ai_feedback') and session.ai_feedback:
            try:
                feedback_data = json.loads(session.ai_feedback)
                session.performance_score = feedback_data.get('overall_score', 'N/A')
                session.confidence_level = feedback_data.get('confidence_level', 'N/A')
                session.communication_score = feedback_data.get('communication_score', 'N/A')
            except:
                session.performance_score = 'N/A'
                session.confidence_level = 'N/A'
                session.communication_score = 'N/A'
        else:
            session.performance_score = 'Pending'
            session.confidence_level = 'Pending'
            session.communication_score = 'Pending'
        
        # Calculate interview duration
        if session.start_time and session.end_time:
            duration = session.end_time - session.start_time
            session.duration_minutes = round(duration.total_seconds() / 60, 1)
        else:
            session.duration_minutes = 'N/A'
    
    return render(request, 'mock_interview/my_mock_interviews.html', {'sessions': sessions})

@login_required
@user_passes_test(lambda u: is_tutor(u) or is_admin(u), login_url='/login/')
def tutor_interview_review_list(request):
    if is_admin(request.user):
        sessions = MockInterviewSession.objects.all().order_by('-start_time')
    else:
        sessions = MockInterviewSession.objects.filter(status='REVIEW_PENDING').order_by('-start_time')
    
    # Add enhanced metrics for tutor review
    for session in sessions:
        session.total_questions = session.turns.count()
        if session.start_time and session.end_time:
            duration = session.end_time - session.start_time
            session.duration_minutes = round(duration.total_seconds() / 60, 1)
        else:
            session.duration_minutes = 'N/A'
    
    return render(request, 'tutor/mock_interview_review_list.html', {'sessions': sessions})

@login_required
@user_passes_test(lambda u: is_tutor(u) or is_admin(u), login_url='/login/')
def tutor_review_interview_detail(request, session_id):
    session = get_object_or_404(MockInterviewSession, id=session_id)
    turns = session.turns.all().order_by('turn_number')
    
    # Get AI analysis if available
    ai_analysis = None
    if hasattr(session, 'ai_feedback') and session.ai_feedback:
        try:
            ai_analysis = json.loads(session.ai_feedback)
        except:
            ai_analysis = None
    
    # Calculate interview metrics
    total_words = sum(len((turn.user_answer or '').split()) for turn in turns)
    avg_response_length = total_words / max(turns.count(), 1)
    
    if request.method == 'POST':
        session.overall_feedback = request.POST.get('overall_feedback', '')
        score = request.POST.get('score')
        if score and score.isdigit():
            session.score = int(score)
        session.status = 'REVIEWED'
        session.save()
        messages.success(request, 'Interview review completed successfully!')
        return redirect('mock_interview:tutor_interview_review_list')
    
    return render(request, 'tutor/mock_interview_review_detail.html', {
        'session': session, 
        'turns': turns,
        'ai_analysis': ai_analysis,
        'interview_metrics': {
            'total_words': total_words,
            'avg_response_length': round(avg_response_length, 1),
            'total_questions': turns.count()
        }
    })

@login_required
@user_passes_test(is_student, login_url='/login/')
@csrf_exempt
def parse_resume_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
    resume_file = request.FILES.get('resume_file')
    if not resume_file:
        return JsonResponse({'error': 'No file provided.'}, status=400)
    
    try:
        resume_text = parse_resume_file(resume_file, filename=resume_file.name)
        if not resume_text.strip():
            return JsonResponse({'error': 'Unable to extract text from resume.'}, status=422)
        
        parsed = extract_structured_from_resume_text(resume_text)
        
        return JsonResponse({
            'success': True,
            'job_role': parsed.get('job_role', ''),
            'skills': parsed.get('skills', []),
            'experience_years': parsed.get('experience_years', 0),
            'education': parsed.get('education', ''),
            'summary': parsed.get('summary', ''),
            'key_achievements': parsed.get('key_achievements', []),
            'industries': parsed.get('industries', []),
            'raw': parsed.get('raw', ''),
        })
    except Exception as e:
        logger.exception("Resume parsing failed")
        return JsonResponse({'error': f'Resume parsing failed: {str(e)}'}, status=500)

@login_required
@user_passes_test(is_student, login_url='/login/')
def review_interview(request, session_id):
    session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
    turns = session.turns.all().order_by('turn_number')
    
    if session.status not in ['COMPLETED', 'REVIEWED']:
        return redirect('mock_interview:main_interview', session_id=session.id)
    
    if session.score is not None:
        # Calculate the degree for the score circle here in Python
        score_deg = session.score * 3.6
    else:
        # If the score is None, set score_deg to 0 or another default value
        score_deg = 0
    
    # Parse AI feedback if available
    ai_feedback = None
    if hasattr(session, 'ai_feedback') and session.ai_feedback:
        try:
            ai_feedback = json.loads(session.ai_feedback)
        except:
            ai_feedback = None
    
    # Calculate enhanced interview metrics
    interview_duration = None
    total_words = 0
    confidence_indicators = []
    
    if session.start_time and session.end_time:
        duration = session.end_time - session.start_time
        interview_duration = duration.total_seconds() / 60
    
    for turn in turns:
        if turn.user_answer:
            words = len(turn.user_answer.split())
            total_words += words
            # Simple confidence indicators based on response patterns
            if words > 50:
                confidence_indicators.append('detailed_responses')
            if any(word in turn.user_answer.lower() for word in ['achieved', 'led', 'managed', 'created']):
                confidence_indicators.append('action_words')
    
    avg_response_length = total_words / max(turns.count(), 1)
    
    return render(request, 'mock_interview/review_interview.html', {
        'session': session,
        'turns': turns,
        'ai_feedback': ai_feedback,
        'transcript': session.turns.all(),
        'score_deg': score_deg,  # Pass the calculated variable to the template
        'interview_metrics': {
            'duration_minutes': round(interview_duration, 1) if interview_duration else None,
            'total_questions': turns.count(),
            'total_words': total_words,
            'avg_response_length': round(avg_response_length, 1),
            'confidence_score': len(set(confidence_indicators)) * 20  # Simple confidence scoring
        }
    })

# -------------------------
# Enhanced AI Feature Endpoints
# -------------------------
@login_required
@user_passes_test(is_student, login_url='/login/')
@csrf_exempt
def get_interview_hints_api(request, session_id):
    """Provide contextual hints during interview with encouraging tone."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
    session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
    
    try:
        payload = json.loads(request.body)
        current_question = payload.get('current_question', '')
        user_struggle_context = payload.get('context', '')
    except:
        return JsonResponse({'error': 'Invalid request data.'}, status=400)
    
    hint_prompt = f"""
    You are Sarah, the encouraging interviewer. A candidate is having difficulty with this question: 
    "{current_question}"
    
    Context about their struggle: {user_struggle_context}
    Position: {session.job_role}
    
    Provide 3 warm, helpful hints that guide them without giving away the answer. Be encouraging and supportive:
    
    1. A gentle thinking approach hint
    2. A structural framework suggestion
    3. An encouraging example direction
    
    Keep Sarah's warm, supportive personality. Use phrases like:
    - "You're on the right track!"
    - "Here's a way to think about it..."
    - "Many candidates find it helpful to..."
    
    Return as JSON: {{"hints": ["encouraging hint 1", "supportive hint 2", "guiding hint 3"]}}
    """
    
    try:
        hints_response = call_ai_model(hint_prompt, max_tokens=400, temperature=0.7)
        hints_data = json.loads(hints_response)
        return JsonResponse({
            'success': True,
            'hints': hints_data.get('hints', []),
            'encouragement': "Remember, you're doing great! Take your time and trust your experience."
        })
    except Exception as e:
        logger.warning(f"Hints generation failed: {e}")
        return JsonResponse({
            'success': True,
            'hints': [
                "You're doing wonderfully! Take a moment to think about your personal experiences.", 
                "Consider using the STAR method: Situation, Task, Action, Result - it's a great framework!",
                "Think of a specific example from your background - specifics always make answers stronger!"
            ],
            'encouragement': "You've got this! Every question is an opportunity to shine."
        })

@login_required
@user_passes_test(is_student, login_url='/login/')
@csrf_exempt  
def practice_question_api(request, session_id):
    """Generate practice questions with Sarah's encouraging style."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
    session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
    
    try:
        payload = json.loads(request.body)
        topic = payload.get('topic', 'general')
        difficulty = payload.get('difficulty', 'medium')
    except:
        return JsonResponse({'error': 'Invalid request data.'}, status=400)
    
    practice_prompt = f"""
    You are Sarah, the warm and encouraging interviewer, creating a practice question.
    
    Topic focus: {topic}
    Difficulty level: {difficulty}
    Position: {session.job_role}
    Key skills: {session.key_skills}
    
    Generate a practice question that:
    1. Matches the difficulty level
    2. Is relevant to the topic and role
    3. Includes Sarah's encouraging introduction
    4. Provides helpful guidance
    
    Return JSON format:
    {{
        "question": "Sarah's warm introduction + the practice question",
        "tips": ["Sarah's encouraging tips"],
        "sample_answer_structure": "Friendly structural guidance",
        "encouragement": "Personal motivational message from Sarah"
    }}
    
    Make it sound like Sarah is personally coaching them!
    """
    
    try:
        practice_response = call_ai_model(practice_prompt, max_tokens=500, temperature=0.8)
        practice_data = json.loads(practice_response)
        return JsonResponse({
            'success': True,
            'question': practice_data.get('question', ''),
            'tips': practice_data.get('tips', []),
            'structure': practice_data.get('sample_answer_structure', ''),
            'encouragement': practice_data.get('encouragement', 'You\'re going to do amazingly well!')
        })
    except Exception as e:
        logger.warning(f"Practice question generation failed: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to generate practice question at this time.'
        })

# -------------------------
# Additional Helper Functions
# -------------------------

def get_interview_statistics(user):
    """Get comprehensive interview statistics for a user."""
    sessions = MockInterviewSession.objects.filter(user=user)
    
    stats = {
        'total_interviews': sessions.count(),
        'completed_interviews': sessions.filter(status='COMPLETED').count(),
        'average_score': 0,
        'total_interview_time': 0,
        'improvement_trend': 'stable'
    }
    
    completed_sessions = sessions.filter(status__in=['COMPLETED', 'REVIEWED'])
    
    if completed_sessions.exists():
        # Calculate average score
        scored_sessions = completed_sessions.exclude(score__isnull=True)
        if scored_sessions.exists():
            stats['average_score'] = round(
                sum(s.score for s in scored_sessions) / scored_sessions.count(), 1
            )
        
        # Calculate total interview time
        timed_sessions = completed_sessions.exclude(start_time__isnull=True, end_time__isnull=True)
        total_seconds = sum(
            (s.end_time - s.start_time).total_seconds() 
            for s in timed_sessions 
            if s.start_time and s.end_time
        )
        stats['total_interview_time'] = round(total_seconds / 60, 1)  # in minutes
        
        # Simple improvement trend (compare last 3 vs previous 3)
        recent_sessions = list(completed_sessions.order_by('-start_time')[:6])
        if len(recent_sessions) >= 6:
            recent_scores = [s.score for s in recent_sessions[:3] if s.score]
            older_scores = [s.score for s in recent_sessions[3:6] if s.score]
            
            if recent_scores and older_scores:
                recent_avg = sum(recent_scores) / len(recent_scores)
                older_avg = sum(older_scores) / len(older_scores)
                
                if recent_avg > older_avg + 5:
                    stats['improvement_trend'] = 'improving'
                elif recent_avg < older_avg - 5:
                    stats['improvement_trend'] = 'declining'
    
    return stats

@login_required
@user_passes_test(is_student, login_url='/login/')
def interview_analytics(request):
    """Show detailed analytics for student's interview performance."""
    user_stats = get_interview_statistics(request.user)
    sessions = MockInterviewSession.objects.filter(
        user=request.user, 
        status__in=['COMPLETED', 'REVIEWED']
    ).order_by('-start_time')[:10]
    
    # Prepare data for charts/graphs
    session_data = []
    for session in sessions:
        data_point = {
            'date': session.start_time.strftime('%Y-%m-%d') if session.start_time else 'N/A',
            'job_role': session.job_role,
            'score': session.score or 0,
            'duration': 0
        }
        
        if session.start_time and session.end_time:
            duration = session.end_time - session.start_time
            data_point['duration'] = round(duration.total_seconds() / 60, 1)
        
        session_data.append(data_point)
    
    return render(request, 'mock_interview/interview_analytics.html', {
        'user_stats': user_stats,
        'session_data': session_data,
        'chart_data_json': json.dumps(session_data)
    })

# -------------------------
# Error Handling and Logging Enhancements
# -------------------------

def log_interview_interaction(session, interaction_type, details, error=None):
    """Enhanced logging for interview interactions."""
    log_data = {
        'session_id': session.id,
        'user_id': session.user.id,
        'interaction_type': interaction_type,
        'details': details,
        'timestamp': timezone.now().isoformat()
    }
    
    if error:
        log_data['error'] = str(error)
        logger.error(f"Interview interaction error: {json.dumps(log_data)}")
    else:
        logger.info(f"Interview interaction: {json.dumps(log_data)}")

# -------------------------
# API Health Check
# -------------------------

@csrf_exempt
def ai_health_check(request):
    """Check if AI services are working properly."""
    health_status = {
        'ai_provider': AI_PROVIDER,
        'text_generation': False,
        'tts_generation': False,
        'gtts_available': True,  # gTTS is always available once installed
        'gtts_functional': False,
        'timestamp': timezone.now().isoformat()
    }
    
    try:
        # Test text generation
        test_response = call_ai_model("Say 'Hello, this is a test!'", model_type="text", max_tokens=50)
        health_status['text_generation'] = bool(test_response and len(test_response.strip()) > 0)
        
        # Test TTS (quick test)
        if health_status['text_generation']:
            try:
                tts_result = call_ai_model("Test", model_type="tts")
                health_status['tts_generation'] = bool(tts_result.get("audio_base64"))
            except:
                pass
            
            try:
                gtts_result = call_ai_model("Test", model_type="gtts")
                health_status['gtts_functional'] = bool(gtts_result.get("audio_url"))
            except:
                pass
                
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    status_code = 200 if health_status['text_generation'] else 503
    return JsonResponse(health_status, status=status_code)

@login_required
def delete_session(request, session_id):
    """
    Deletes a single mock interview session for the logged-in user.
    """
    if request.method == 'POST':
        session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
        session.delete()
    return redirect('mock_interview:my_mock_interviews')

@login_required
def clear_all_sessions(request):
    """
    Deletes all mock interview sessions for the logged-in user.
    """
    if request.method == 'POST':
        MockInterviewSession.objects.filter(user=request.user).delete()
    return redirect('mock_interview:my_mock_interviews')