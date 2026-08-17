import React, { useState, useEffect } from 'react';
import { MessageCircle, Trophy, Send, Loader2 } from 'lucide-react';
import { useAuth } from '../store/AuthContext';
import { motion, AnimatePresence } from 'motion/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchCommunityChat, postCommunityMessage, fetchLeaderboard, queryKeys, handleApiError } from '../api';
import { toast } from 'sonner';

export default function CommunityPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [newPost, setNewPost] = useState('');
  const [isPosting, setIsPosting] = useState(false);
  const [isTabActive, setIsTabActive] = useState(!document.hidden);

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsTabActive(!document.hidden);
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  const { data: feed = [], isLoading: isFeedLoading } = useQuery({
    queryKey: queryKeys.community.messages(50),
    queryFn: () => fetchCommunityChat(50),
    refetchInterval: isTabActive ? 15000 : false, // Poll every 15s if active
  });

  const { data: leaderboard = [], isLoading: isLeaderboardLoading } = useQuery({
    queryKey: queryKeys.leaderboard,
    queryFn: () => fetchLeaderboard(5),
  });

  const handlePublish = async () => {
    if (!newPost.trim() || !user || isPosting) return;
    setIsPosting(true);
    try {
      await postCommunityMessage(user.username, newPost.trim());
      setNewPost('');
      queryClient.invalidateQueries({ queryKey: queryKeys.community.messages(50) });
    } catch (e: unknown) {
      const normErr = handleApiError(e);
      toast.error(normErr.message);
    } finally {
      setIsPosting(false);
    }
  };

  const getRankBadge = (rank: number) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return '⭐';
  };

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto w-full pt-8 grid grid-cols-1 lg:grid-cols-3 gap-8 pb-24 lg:pb-8">
      
      {/* Left Column: Feed */}
      <div className="lg:col-span-2 space-y-6 flex flex-col h-[calc(100vh-140px)] md:h-auto">
        <div className="flex items-center justify-between mb-2 shrink-0">
          <h1 className="text-2xl font-bold text-graphite">Чат сообщества</h1>
        </div>

        {/* Create Post */}
        <div className="bg-white p-4 rounded-3xl border border-sand shadow-sm flex gap-4 shrink-0">
          <div className="w-10 h-10 rounded-full bg-primary/10 shrink-0 flex items-center justify-center font-bold text-primary">
            {(user?.username || 'В').charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 flex gap-2">
            <input 
              type="text" 
              value={newPost}
              onChange={(e) => setNewPost(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handlePublish()}
              placeholder="Напишите сообщение..." 
              maxLength={1000}
              disabled={isPosting}
              className="w-full bg-cream rounded-2xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 border border-sand focus:border-primary/30"
            />
            <button 
              onClick={handlePublish}
              disabled={!newPost.trim() || isPosting}
              className="bg-primary text-white p-3 rounded-2xl disabled:opacity-50 transition-all shrink-0 hover:bg-primary/90"
            >
              {isPosting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Feed List */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2 hide-scrollbar">
          {isFeedLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-white p-5 rounded-3xl border border-sand shadow-sm animate-pulse h-28" />
            ))
          ) : feed.length > 0 ? (
            <AnimatePresence>
              {feed.map((post) => (
                <motion.div 
                  key={post.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`bg-white p-5 rounded-3xl border border-sand shadow-sm ${post.username === user?.username ? 'border-primary/20 bg-primary/5' : ''}`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 rounded-full bg-primary/10 shrink-0 flex items-center justify-center font-bold text-primary text-xs">
                      {post.username.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="font-bold text-sm text-graphite flex items-center gap-2">
                        {post.username}
                        {post.username === user?.username && <span className="text-[10px] bg-primary text-white px-2 py-0.5 rounded-full font-medium">Вы</span>}
                      </p>
                      <p className="text-[10px] text-graphite/50">{new Date(post.timestamp).toLocaleString('ru-RU')}</p>
                    </div>
                  </div>
                  <p className="text-graphite/90 text-sm leading-relaxed whitespace-pre-wrap">{post.text}</p>
                </motion.div>
              ))}
            </AnimatePresence>
          ) : (
            <div className="text-center p-8 bg-cream rounded-2xl border border-sand/50 text-graphite/60">
              Начните первое сообщение сообщества
            </div>
          )}
        </div>
      </div>

      {/* Right Column: Leaderboard Widget */}
      <div className="space-y-6 hidden lg:block">
        <div className="bg-gradient-to-br from-primary to-primary-light p-6 rounded-3xl text-white shadow-lg relative overflow-hidden">
          <Trophy className="absolute -right-6 -bottom-6 w-32 h-32 text-white/10" />
          <h2 className="font-bold text-xl mb-6 relative z-10 flex items-center gap-2">
            <Trophy className="w-5 h-5" /> Топ активистов
          </h2>
          <div className="space-y-3 relative z-10">
            {isLeaderboardLoading ? (
               Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-10 bg-white/10 animate-pulse rounded-2xl" />
              ))
            ) : leaderboard.length > 0 ? (
              leaderboard.slice(0, 5).map((u, idx) => (
                <div 
                  key={u.id} 
                  className={`flex items-center justify-between p-3 rounded-2xl ${u.id.toString() === user?.id?.toString() ? 'bg-white/20 backdrop-blur-sm shadow-sm' : ''}`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{getRankBadge(idx + 1)}</span>
                    <span className={`font-bold text-sm ${u.id.toString() === user?.id?.toString() ? 'text-white' : 'text-white/90'}`}>
                      {u.username}
                    </span>
                  </div>
                  <span className="font-mono text-sm font-bold bg-black/20 px-2 py-1 rounded-lg">{u.points}</span>
                </div>
              ))
            ) : (
              <div className="text-white/60 text-sm">Пока нет данных</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
