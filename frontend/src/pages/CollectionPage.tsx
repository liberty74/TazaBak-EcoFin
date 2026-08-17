import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Award, Copy, Check, Sparkles, AlertCircle, Info, ArrowLeft, Calendar, User } from 'lucide-react';
import { fetchUserNfts } from '../api/users';
import { queryKeys } from '../api/queryKeys';
import { useAuth } from '../store/AuthContext';
import { useLocaleTheme } from '../store/LocaleThemeContext';
import EcoNftImage from '../components/common/EcoNftImage';
import type { EcoNFT } from '../api/types';
import { motion, AnimatePresence } from 'motion/react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

export default function CollectionPage() {
  const { user } = useAuth();
  const { t } = useLocaleTheme();
  const navigate = useNavigate();
  const [selectedNft, setSelectedNft] = useState<EcoNFT | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const { data: nfts = [], isLoading, isError } = useQuery({
    queryKey: queryKeys.user.nfts(user?.id),
    queryFn: () => fetchUserNfts(user?.id || ''),
    enabled: !!user?.id,
  });

  const handleCopyId = (tokenId: string) => {
    navigator.clipboard.writeText(tokenId);
    setCopiedId(tokenId);
    toast.success(t('tokenCopied'));
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto w-full pt-8 pb-24 lg:pb-8 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-2">
        <div>
          <h1 className="text-3xl font-extrabold text-primary tracking-tight">{t('collectionTitle')}</h1>
          <p className="text-graphite/60 text-sm">{t('collectionSub')}</p>
        </div>
        <button 
          onClick={() => navigate('/shop')}
          className="bg-primary/10 text-primary hover:bg-primary hover:text-white font-bold text-sm px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-colors shadow-sm"
        >
          <Sparkles className="w-4 h-4" />
          <span>{t('mintTab')}</span>
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="animate-pulse bg-white border border-sand rounded-3xl p-5 h-64 shadow-sm" />
          ))}
        </div>
      ) : isError ? (
        <div className="bg-critical/10 border border-critical/20 rounded-2xl p-6 text-center text-critical font-medium">
          Не удалось загрузить коллекцию NFT. Пожалуйста, запустите FastAPI бэкенд.
        </div>
      ) : nfts.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {nfts.map((nft) => (
            <motion.div
              key={nft.id}
              layoutId={`nft-card-${nft.id}`}
              whileHover={{ y: -4, boxShadow: '0 10px 15px -3px rgba(0,0,0,0.05)' }}
              className="bg-white border border-sand rounded-3xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col items-center text-center cursor-pointer relative group overflow-hidden"
              onClick={() => setSelectedNft(nft)}
            >
              {/* NFT SVG preview */}
              <div className="w-full aspect-square bg-cream rounded-2xl mb-4 overflow-hidden flex items-center justify-center border border-sand shadow-inner p-2 drop-shadow-sm">
                <EcoNftImage svgContent={nft.svg_content} title={nft.title} className="w-full h-full object-contain" />
              </div>

              <h3 className="font-extrabold text-base text-graphite mb-1 truncate w-full">{nft.title}</h3>
              <p className="text-[10px] text-graphite/40 font-mono mb-4">Token ID: {nft.token_id.substring(0, 8)}...</p>
              
              <div className="mt-auto w-full flex gap-2">
                <button 
                  className="flex-1 bg-primary/10 text-primary hover:bg-primary hover:text-white transition-colors py-2 rounded-xl text-xs font-bold"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedNft(nft);
                  }}
                >
                  {t('detailsBtn')}
                </button>
                <button
                  className="p-2 bg-cream hover:bg-sand/30 rounded-xl text-graphite/50 hover:text-graphite transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCopyId(nft.token_id);
                  }}
                >
                  {copiedId === nft.token_id ? <Check className="w-4 h-4 text-primary" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="max-w-md mx-auto w-full bg-white border border-sand rounded-3xl p-8 text-center shadow-sm">
          <div className="w-16 h-16 bg-cream rounded-2xl flex items-center justify-center text-primary mx-auto mb-6">
            <Award className="w-8 h-8" />
          </div>
          <p className="text-graphite/80 font-medium mb-6 leading-relaxed">
            {t('emptyCollection')}
          </p>
          <button 
            onClick={() => navigate('/shop')}
            className="w-full bg-primary text-white font-bold py-3.5 rounded-xl shadow-md hover:bg-primary/95 transition-all flex items-center justify-center gap-2"
          >
            <Sparkles className="w-5 h-5" />
            <span>Создать Eco-NFT</span>
          </button>
        </div>
      )}

      {/* Detailed view Modal */}
      <AnimatePresence>
        {selectedNft && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setSelectedNft(null)}
            />
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="relative bg-white rounded-3xl p-6 md:p-8 max-w-lg w-full shadow-2xl z-10 space-y-6 max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-center">
                <button 
                  onClick={() => setSelectedNft(null)}
                  className="p-2 hover:bg-cream rounded-full text-graphite/50 transition-colors"
                >
                  <ArrowLeft className="w-5 h-5" />
                </button>
                <span className="text-xs font-bold text-primary bg-primary/10 px-3 py-1 rounded-full uppercase tracking-wider">Eco-Achievement</span>
              </div>

              {/* Large SVG rendering */}
              <div className="w-full aspect-square bg-cream rounded-2xl overflow-hidden flex items-center justify-center border-4 border-sand shadow-inner p-6 drop-shadow-md">
                <EcoNftImage svgContent={selectedNft.svg_content} title={selectedNft.title} className="w-full h-full object-contain" />
              </div>

              <div className="space-y-4">
                <div>
                  <h3 className="font-extrabold text-2xl text-graphite leading-tight">{selectedNft.title}</h3>
                  <div className="flex items-center gap-2 mt-2 bg-cream rounded-xl p-3 border border-sand">
                    <span className="text-xs text-graphite/50 font-mono select-all break-all flex-1">{selectedNft.token_id}</span>
                    <button
                      className="p-2 bg-white hover:bg-cream border border-sand rounded-lg text-graphite/50 hover:text-graphite transition-colors"
                      onClick={() => handleCopyId(selectedNft.token_id)}
                    >
                      {copiedId === selectedNft.token_id ? <Check className="w-3.5 h-3.5 text-primary" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-2 border-t border-sand">
                  <div className="flex items-center gap-2 text-sm text-graphite/70">
                    <User className="w-4 h-4 text-primary" />
                    <div>
                      <p className="text-[10px] text-graphite/40 leading-none">{t('nftOwner')}</p>
                      <p className="font-bold mt-1 text-xs truncate max-w-[120px]">{user?.username}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-graphite/70">
                    <Calendar className="w-4 h-4 text-primary" />
                    <div>
                      <p className="text-[10px] text-graphite/40 leading-none">{t('nftDate')}</p>
                      <p className="font-bold mt-1 text-xs">{new Date(selectedNft.creation_date).toLocaleDateString('ru-RU')}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-sand/30 p-4 rounded-xl flex gap-2 items-start text-xs text-graphite/60">
                  <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                  <p>{t('nftDisclaimer')}</p>
                </div>
              </div>

              <button 
                onClick={() => setSelectedNft(null)}
                className="w-full bg-primary hover:bg-primary/95 text-white py-3 rounded-xl font-bold transition-colors"
              >
                {t('excellentBtn')}
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
