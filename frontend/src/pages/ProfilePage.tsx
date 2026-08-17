import React from 'react';
import { useAuth } from '../store/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { fetchUserProfile, fetchUserTransactions, fetchUserNfts } from '../api';
import { queryKeys } from '../api/queryKeys';
import { Trophy, History, Wallet, Sparkles, Image as ImageIcon } from 'lucide-react';
import { motion } from 'motion/react';
import EcoNftImage from '../components/common/EcoNftImage';

export default function ProfilePage() {
  const { user } = useAuth();
  
  const { data: profile, isLoading: isProfileLoading } = useQuery({
    queryKey: queryKeys.user.profile(user?.id),
    queryFn: () => fetchUserProfile(user?.id || ''),
    enabled: !!user?.id,
  });

  const { data: transactions = [], isLoading: isTxLoading } = useQuery({
    queryKey: queryKeys.user.transactions(user?.id),
    queryFn: () => fetchUserTransactions(user?.id || ''),
    enabled: !!user?.id,
  });

  const { data: nfts = [], isLoading: isNftsLoading } = useQuery({
    queryKey: queryKeys.user.nfts(user?.id),
    queryFn: () => fetchUserNfts(user?.id || ''),
    enabled: !!user?.id,
  });

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto w-full pt-8 pb-24 lg:pb-8 space-y-8">
      {/* Profile Header */}
      <div className="bg-white border border-sand rounded-3xl p-6 md:p-8 shadow-sm relative overflow-hidden">
        <div className="flex flex-col md:flex-row items-center gap-6 relative z-10">
          <div className="w-24 h-24 rounded-full bg-primary/10 border-4 border-white shadow-md flex items-center justify-center text-4xl font-bold text-primary">
            {profile?.username?.charAt(0).toUpperCase() || user?.username?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="text-center md:text-left flex-1">
            <h1 className="text-3xl font-bold text-graphite mb-1">{profile?.username || user?.username}</h1>
            <p className="text-graphite/60 capitalize mb-4">{profile?.role || user?.role}</p>
            <div className="flex flex-wrap gap-3 justify-center md:justify-start">
              <div className="bg-cream border border-sand px-4 py-2 rounded-xl flex items-center gap-2">
                <Wallet className="w-4 h-4 text-primary" />
                <span className="font-bold">{profile?.points || 0} баллов</span>
              </div>
              <div className="bg-cream border border-sand px-4 py-2 rounded-xl flex items-center gap-2">
                <Trophy className="w-4 h-4 text-warning" />
                <span className="font-bold">{profile?.status_tier || 'Новичок'}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4 pointer-events-none" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* NFTs Collection */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-graphite flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            Моя Коллекция (Eco-NFT)
          </h2>
          <div className="bg-white border border-sand rounded-3xl p-6 shadow-sm min-h-[300px]">
            {isNftsLoading ? (
              <div className="grid grid-cols-2 gap-4">
                {[1,2,3,4].map(i => <div key={i} className="animate-pulse bg-sand rounded-2xl aspect-square" />)}
              </div>
            ) : nfts.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {nfts.map((nft) => (
                  <motion.div 
                    key={nft.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center"
                  >
                    <div className="w-full aspect-square bg-cream rounded-2xl mb-2 overflow-hidden flex items-center justify-center border-2 border-sand shadow-inner p-2 relative group">
                      <EcoNftImage 
                        svgContent={nft.svg_content} 
                        title={nft.title}
                        className="w-full h-full object-contain drop-shadow-sm group-hover:scale-110 transition-transform"
                      />
                    </div>
                    <h3 className="font-bold text-xs text-center line-clamp-1">{nft.title}</h3>
                    <p className="text-[10px] text-graphite/40 font-mono">ID: {nft.token_id.substring(0, 8)}...</p>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-graphite/40 py-12">
                <ImageIcon className="w-12 h-12 mb-2 opacity-20" />
                <p>Коллекция пуста</p>
              </div>
            )}
          </div>
        </div>

        {/* Transaction History */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-graphite flex items-center gap-2">
            <History className="w-5 h-5 text-primary" />
            История транзакций
          </h2>
          <div className="bg-white border border-sand rounded-3xl shadow-sm overflow-hidden flex flex-col h-[400px]">
            <div className="flex-1 overflow-y-auto p-2">
              {isTxLoading ? (
                 Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="animate-pulse p-4 border-b border-sand last:border-0 flex justify-between">
                    <div className="space-y-2">
                      <div className="h-4 bg-sand rounded w-32"></div>
                      <div className="h-3 bg-sand rounded w-24"></div>
                    </div>
                    <div className="h-4 bg-sand rounded w-12"></div>
                  </div>
                ))
              ) : transactions.length > 0 ? (
                transactions.map((tx) => (
                  <div key={tx.id} className="p-4 border-b border-sand last:border-0 flex items-center justify-between hover:bg-sand/10 transition-colors">
                    <div>
                      <p className="font-bold text-sm text-graphite">{tx.description}</p>
                      <p className="text-xs text-graphite/50">{new Date(tx.created_at).toLocaleString('ru-RU')}</p>
                    </div>
                    <div className={`font-bold text-sm ${tx.amount > 0 ? 'text-primary' : 'text-graphite'}`}>
                      {tx.amount > 0 ? '+' : ''}{tx.amount}
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-full flex items-center justify-center text-graphite/40">
                  Нет транзакций
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
