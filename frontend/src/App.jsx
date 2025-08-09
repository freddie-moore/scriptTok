import React, { useState, useEffect, useCallback } from 'react';

import { Settings, Copy, Check, Loader2, Play, Key, Eye, EyeOff } from 'lucide-react';



const App = () => {

  // State management

  const [apiKeys, setApiKeys] = useState({

    gemini: '',

    apify: ''

  });

  const url = "https://there-injured-artificial-months.trycloudflare.com";

  const [showApiModal, setShowApiModal] = useState(false);

  const [showKeys, setShowKeys] = useState({ gemini: false, apify: false });

  const [profileName, setProfileName] = useState('');

  const [topic, setTopic] = useState('');

  const [taskId, setTaskId] = useState(null);

  const [status, setStatus] = useState('');

  const [currentState, setCurrentState] = useState(''); // Track the current backend state

  const [script, setScript] = useState('');

  const [isLoading, setIsLoading] = useState(false);

  const [error, setError] = useState('');

  const [copied, setCopied] = useState(false);



  // Progress calculation based on backend states

  const getProgressInfo = (state) => {

    const states = {

      'SCRAPING': { progress: 25, label: 'Scraping TikTok content...' },

      'ANALYZING': { progress: 50, label: 'Analyzing creator style...' },

      'GENERATING': { progress: 75, label: 'Generating your script...' },

      'SUCCESS': { progress: 100, label: 'Script generated successfully!' }

    };

    return states[state] || { progress: 0, label: 'Starting...' };

  };



  // Check for API keys on component mount

  useEffect(() => {

    // Show modal if keys are missing on initial load

    if (!apiKeys.gemini || !apiKeys.apify) {

      setShowApiModal(true);

    }

  }, [apiKeys.gemini, apiKeys.apify]);



  // Save API keys (just close modal since we're using state)

  const saveApiKeys = () => {

    setShowApiModal(false);

  };



  // Clear API keys

  const clearApiKeys = () => {

    setApiKeys({ gemini: '', apify: '' });

    setShowApiModal(true);

  };



  // Poll status endpoint

  const pollStatus = useCallback(async (id) => {

    let retryCount = 0;

    const maxRetries = 3;
   

    const poll = async () => {

      try {

        const response = await fetch(`${url}/api/status/${id}`);
2
       

        if (!response.ok) {

          throw new Error('Status check failed');

        }

       

        const data = await response.json();



        if (data.state === 'SUCCESS') {

          setCurrentState('SUCCESS');

          setStatus('Script generated successfully!');

          setScript(data.result.script);

          setIsLoading(false);

          return; // Stop polling

        } else if (data.state === 'FAILURE') {

          setStatus('An unexpected error was encountered.')

          setError(data.status || 'Script generation failed');

          setIsLoading(false);

          setCurrentState('');

          return; // Stop polling

        } else {

          // Update current state and status for progress tracking

          setCurrentState(data.state);

          setStatus(data.status)

        }

       

        // Continue polling after 2 seconds

        setTimeout(poll, 2000);

        retryCount = 0; // Reset retry count on successful request

       

      } catch (err) {

        retryCount++;

        if (retryCount <= maxRetries) {

          setTimeout(poll, 3000); // Retry after 3 seconds

        } else {

          setError('Lost connection while fetching status. Please wait and try again.');

          setIsLoading(false);

          setCurrentState('');

        }

      }

    };

   

    poll();

  }, []);



  // Generate script

  const generateScript = async () => {

    if (!profileName.trim() || !topic.trim()) {

      setError('Please fill in both the TikTok username and video idea.');

      return;

    }



    if (!apiKeys.gemini || !apiKeys.apify) {

      setShowApiModal(true);

      return;

    }



    setIsLoading(true);

    setError('');

    setScript('');

    setStatus('Starting script generation...');

    setCurrentState(''); // Reset state



    try {
      const requestBody = {
        profile_name: profileName,
        topic: topic,
        gemini_api_key: apiKeys.gemini,
        apify_api_key: apiKeys.apify
      };

      console.log('Sending request to:', `${url}/api/generate-script`);
      console.log('Request body:', requestBody);

      const response = await fetch(`${url}/api/generate-script`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error('Could not start the generation process');
      }

      const data = await response.json();
      setTaskId(data.task_id);
      pollStatus(data.task_id);



    } catch (err) {

      setError('Could not start the generation process. Please check your connection and try again.');

      setIsLoading(false);

      setCurrentState('');

    }

  };



  // Copy to clipboard

  const copyToClipboard = () => {

    // Use the modern clipboard API if available, otherwise fall back to execCommand

    if (navigator.clipboard && navigator.clipboard.writeText) {

        navigator.clipboard.writeText(script).then(() => {

            setCopied(true);

            setTimeout(() => setCopied(false), 2000);

        });

    } else {

        // Fallback for older browsers or insecure contexts

        const textArea = document.createElement('textarea');

        textArea.value = script;

        // Make the textarea non-editable and invisible

        textArea.style.position = 'absolute';

        textArea.style.left = '-9999px';

        document.body.appendChild(textArea);

        textArea.focus();

        textArea.select();

        try {

            document.execCommand('copy');

            setCopied(true);

            setTimeout(() => setCopied(false), 2000);

        } catch (err) {

            console.error('Fallback copy failed', err);

        }

        document.body.removeChild(textArea);

    }

  };



  // Get current progress info

  const progressInfo = getProgressInfo(currentState);



  return (

    <div className="min-h-screen bg-gray-900 text-white font-sans">

      {/* Header */}

      <header className="bg-gray-800 border-b border-gray-700">

        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">

          <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">

            scriptTok

          </h1>

          <button

            onClick={() => setShowApiModal(true)}

            className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"

          >

            <Settings size={18} />

            <span className="hidden sm:inline">API Keys</span>

          </button>

        </div>

      </header>



      {/* Main Content */}

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

       

        {/* Introduction Box */}

        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-8">

            <h2 className="text-2xl font-bold mb-3 text-white">

                Welcome to scriptTok!

            </h2>

            <p className="text-gray-300 leading-relaxed">

                This project allows you to generate content in the style of your favourite TikTok creators. Simply input the username and video idea into the boxes below and watch the magic unfold.

            </p>

            <p className="text-gray-300 mt-3 leading-relaxed">

                Usage of this project requires an <a href="https://console.apify.com/settings/integrations" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:underline font-medium">Apify</a> and a <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:underline font-medium">Gemini</a> API key. All keys are stored locally.

            </p>

        </div>



        <div className="grid lg:grid-cols-2 gap-8">

          {/* Left Column - Input Form */}

          <div className="space-y-6">

            <div>

              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">

                <Play size={20} />

                Generate Your Script

              </h2>

             

              <div className="space-y-4">

                <div>

                  <label htmlFor="username" className="block text-sm font-medium mb-2">

                    TikTok Username

                  </label>

                  <div className="flex items-center w-full">

                    <span className="px-3 py-3 bg-gray-800 border border-gray-600 border-r-0 rounded-l-lg text-gray-400">

                      @

                    </span>

                    <input

                      id="username"

                      type="text"

                      value={profileName.startsWith('@') ? profileName.slice(1) : profileName}

                      onChange={(e) => setProfileName(e.target.value.startsWith('@') ? e.target.value : `@${e.target.value}`)}

                      placeholder="username"

                      className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-r-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"

                    />

                  </div>

                </div>





                <div>

                  <label htmlFor="topic" className="block text-sm font-medium mb-2">

                    Video Idea

                  </label>

                  <textarea

                    id="topic"

                    value={topic}

                    onChange={(e) => setTopic(e.target.value)}

                    placeholder="Describe your video idea in detail..."

                    rows={4}

                    className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all resize-none"

                  />

                </div>



                <button

                  onClick={generateScript}

                  disabled={isLoading || !profileName.trim() || !topic.trim()}

                  className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-600 disabled:to-gray-600 disabled:cursor-not-allowed rounded-lg font-semibold transition-all flex items-center justify-center gap-2"

                >

                  {isLoading ? (

                    <>

                      <Loader2 size={20} className="animate-spin" />

                      Generating...

                    </>

                  ) : (

                    <>

                      <Play size={20} />

                      Generate Script

                    </>

                  )}

                </button>

              </div>

            </div>

          </div>



          {/* Right Column - Status & Results */}

          <div className="space-y-6">
            {/* Status Display */}
            {(isLoading || status) && (
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-3">Status</h3>
                <div className="flex items-center gap-3">
                  {isLoading && <Loader2 size={20} className="animate-spin text-purple-400" />}
                  <p className="text-gray-300">{status}</p>
                </div>

                {isLoading && (

                  <div className="mt-4 space-y-2">

                    <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">

                      <div 

                        className="bg-gradient-to-r from-purple-500 to-pink-500 h-3 rounded-full transition-all duration-500 ease-out"

                        style={{ width: `${progressInfo.progress}%` }}

                      ></div>

                    </div>

                  </div>

                )}

              </div>

            )}



            {/* Error Display */}

            {error && (

              <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">

                <p className="text-red-400">{error}</p>

              </div>

            )}



            {/* Script Result */}

            {script && (

              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">

                <div className="flex items-center justify-between mb-4">

                  <h3 className="text-lg font-semibold">Your Script</h3>

                  <button

                    onClick={copyToClipboard}

                    className="flex items-center gap-2 px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors text-sm"

                  >

                    {copied ? (

                      <>

                        <Check size={16} />

                        Copied!

                      </>

                    ) : (

                      <>

                        <Copy size={16} />

                        Copy Script

                      </>

                    )}

                  </button>

                </div>

                <div className="bg-gray-900 rounded-lg p-4 border border-gray-600 max-h-96 overflow-y-auto">

                  <pre className="text-sm text-gray-100 whitespace-pre-wrap font-mono">

                    <code>{script}</code>

                  </pre>

                </div>

              </div>

            )}

          </div>

        </div>

      </main>



      {/* API Keys Modal */}

      {showApiModal && (

        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">

          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700">

            <div className="flex items-center gap-2 mb-4">

              <Key size={20} />

              <h3 className="text-lg font-semibold">API Configuration</h3>

            </div>

           

            <div className="space-y-4">

              <div>

                <label className="block text-sm font-medium mb-2">Gemini API Key</label>

                <div className="relative">

                  <input

                    type={showKeys.gemini ? "text" : "password"}

                    value={apiKeys.gemini}

                    onChange={(e) => setApiKeys(prev => ({ ...prev, gemini: e.target.value }))}

                    placeholder="Enter your Gemini API key"

                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 pr-10"

                  />

                  <button

                    type="button"

                    onClick={() => setShowKeys(prev => ({ ...prev, gemini: !prev.gemini }))}

                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-200"

                  >

                    {showKeys.gemini ? <EyeOff size={16} /> : <Eye size={16} />}

                  </button>

                </div>

              </div>



              <div>

                <label className="block text-sm font-medium mb-2">Apify API Key</label>

                <div className="relative">

                  <input

                    type={showKeys.apify ? "text" : "password"}

                    value={apiKeys.apify}

                    onChange={(e) => setApiKeys(prev => ({ ...prev, apify: e.target.value }))}

                    placeholder="Enter your Apify API key"

                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 pr-10"

                  />

                  <button

                    type="button"

                    onClick={() => setShowKeys(prev => ({ ...prev, apify: !prev.apify }))}

                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-200"

                  >

                    {showKeys.apify ? <EyeOff size={16} /> : <Eye size={16} />}

                  </button>

                </div>

              </div>

            </div>



            <div className="flex gap-3 mt-6">

              <button

                onClick={saveApiKeys}

                disabled={!apiKeys.gemini || !apiKeys.apify}

                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors"

              >

                Save Keys

              </button>

              <button

                onClick={clearApiKeys}

                className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg font-semibold transition-colors"

              >

                Clear

              </button>

            </div>



            <p className="text-xs text-gray-400 mt-4 text-center">

              Your API keys are stored in memory during your session and sent securely to the backend for processing.

            </p>

          </div>

        </div>

      )}

    </div>

  );

};



export default App;