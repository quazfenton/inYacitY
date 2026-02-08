import React, { useState } from 'react';
import { Send, Loader2, CheckCircle } from 'lucide-react';
import { subscribeToCity } from '../services/apiService';

interface SubscribeFormProps {
  cityId?: string;
  cityName?: string;
}

const SubscribeForm: React.FC<SubscribeFormProps> = ({ cityId, cityName = 'selected city' }) => {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'IDLE' | 'LOADING' | 'SUCCESS' | 'ERROR'>('IDLE');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!cityId) {
      setStatus('ERROR');
      setMessage('Please select a city first');
      return;
    }

    setStatus('LOADING');
    setMessage('');
    
    try {
      await subscribeToCity(email, cityId);
      setStatus('SUCCESS');
      setMessage(`Connected to ${cityName} network.`);
      setEmail('');
    } catch (error: any) {
      setStatus('ERROR');
      setMessage(error.message || 'Subscription failed. Try again.');
    }
  };

  if (status === 'SUCCESS') {
    return (
      <div className="p-4 border border-acid bg-acid/10 text-acid font-mono text-sm text-center animate-pulse">
        <CheckCircle className="inline-block w-5 h-5 mr-2 mb-1" />
        {message}
        <button 
          onClick={() => {
            setStatus('IDLE');
            setMessage('');
          }} 
          className="block w-full mt-2 text-xs underline decoration-dotted hover:text-white"
        >
          [SUBSCRIBE ANOTHER]
        </button>
      </div>
    );
  }

  if (status === 'ERROR') {
    return (
      <div className="p-4 border border-red-500 bg-red-500/10 text-red-400 font-mono text-sm text-center">
        {message}
        <button 
          onClick={() => {
            setStatus('IDLE');
            setMessage('');
          }} 
          className="block w-full mt-2 text-xs underline decoration-dotted hover:text-white"
        >
          [TRY AGAIN]
        </button>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="mb-2 font-mono text-xs text-zinc-500 uppercase tracking-widest">
        Join the Network
      </div>
      <form onSubmit={handleSubmit} className="relative group">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="ENTER_EMAIL_ADDRESS"
          disabled={!cityId}
          className="w-full bg-transparent border-b border-zinc-700 py-3 text-zinc-100 font-mono focus:outline-none focus:border-acid transition-colors duration-300 placeholder-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={status === 'LOADING' || !cityId}
          className="absolute right-0 top-2 text-zinc-500 group-hover:text-acid transition-colors duration-300 disabled:opacity-50"
        >
          {status === 'LOADING' ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
        </button>
      </form>
      <p className="mt-2 text-[10px] text-zinc-600 font-mono">
        * Weekly encrypted drops for {cityName}. No spam. Unsub anytime.
      </p>
    </div>
  );
};

export default SubscribeForm;