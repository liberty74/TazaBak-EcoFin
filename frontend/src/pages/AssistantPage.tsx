import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Trash2 } from 'lucide-react';
import { motion } from 'motion/react';
import { chatWithAssistant, handleApiError } from '../api';
import { useAuth } from '../store/AuthContext';
import { toast } from 'sonner';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export default function AssistantPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = sessionStorage.getItem('ai_chat_history');
      const parsed: unknown = saved ? JSON.parse(saved) : null;
      if (Array.isArray(parsed) && parsed.every((item) =>
        typeof item === 'object' && item !== null &&
        typeof (item as Message).id === 'string' &&
        ((item as Message).role === 'user' || (item as Message).role === 'assistant') &&
        typeof (item as Message).content === 'string'
      )) return parsed as Message[];
    } catch {
      sessionStorage.removeItem('ai_chat_history');
    }
    return [
      { id: '1', role: 'assistant' as const, content: 'Привет! Я Баки — AI-помощник проекта TazaBAK. Спроси меня, как сортировать отходы, где найти баки или как помочь приютам!' }
    ];
  });
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [assistantMode, setAssistantMode] = useState<'online' | 'offline'>('online');
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
    sessionStorage.setItem('ai_chat_history', JSON.stringify(messages));
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    
    const userText = input.trim();
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: userText };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await chatWithAssistant(userText, user?.id);
      setAssistantMode(response.provider === 'google-gemini' ? 'online' : 'offline');
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response
      }]);
    } catch (e: unknown) {
      const normErr = handleApiError(e);
      toast.error(normErr.message);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Извините, произошла ошибка: ${normErr.message}. Попробуйте спросить ещё раз.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    const initial = [{ id: '1', role: 'assistant' as const, content: 'Привет! Я Баки — AI-помощник проекта TazaBAK. Спроси меня, как сортировать отходы, где найти баки или как помочь приютам!' }];
    setMessages(initial);
    sessionStorage.removeItem('ai_chat_history');
  };

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto w-full bg-background relative">
      {/* Header */}
      <div className="bg-white px-6 py-4 border-b border-sand shrink-0 flex items-center justify-between z-10 shadow-sm pt-8">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center text-primary">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-graphite">Баки AI</h1>
            <p className="text-xs text-primary font-medium flex items-center gap-1">
              <span className={`w-2 h-2 rounded-full ${assistantMode === 'online' ? 'bg-primary-light animate-pulse' : 'bg-warning'}`} />
              {assistantMode === 'online' ? 'ИИ подключён' : 'Офлайн-режим'}
            </p>
          </div>
        </div>
        <button onClick={clearChat} className="p-2 text-graphite/40 hover:text-critical transition-colors" title="Очистить историю">
          <Trash2 className="w-5 h-5" />
        </button>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.map((msg) => (
          <motion.div 
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-cream text-primary' : 'bg-primary text-white'}`}>
              {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
            </div>
            <div className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed whitespace-pre-wrap ${
              msg.role === 'user' 
                ? 'bg-primary text-white rounded-tr-sm' 
                : 'bg-white border border-sand text-graphite rounded-tl-sm shadow-sm'
            }`}>
              {msg.content}
            </div>
          </motion.div>
        ))}
        {isLoading && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="flex gap-4"
          >
            <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5" />
            </div>
            <div className="bg-white border border-sand rounded-2xl rounded-tl-sm p-4 shadow-sm flex items-center gap-2 text-graphite/50">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Баки формулирует ответ...</span>
            </div>
          </motion.div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-sand shrink-0 pb-24 lg:pb-4">
        <div className="flex gap-2">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Спросите Баки о чём угодно..." 
            className="flex-1 bg-cream border border-sand/50 rounded-2xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            disabled={isLoading}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="bg-primary text-white p-3 rounded-2xl disabled:opacity-50 hover:bg-primary/90 transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
