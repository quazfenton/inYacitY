/**
 * React hook for event comments with rate limiting
 * Handles posting, fetching, deleting, and liking comments
 */

import { useState, useCallback, useEffect } from 'react';

interface Comment {
  comment_id: string;
  event_id: string;
  author_name: string;
  text: string;
  created_at: string;
  updated_at?: string;
  likes: number;
  is_approved: boolean;
}

interface CommentsResponse {
  success: boolean;
  event_id: string;
  comments: Comment[];
  total_count: number;
  limit: number;
  offset: number;
  timestamp: string;
}

interface PostCommentResponse {
  success: boolean;
  comment_id: string;
  message: string;
  is_approved: boolean;
  timestamp: string;
  rate_limited?: boolean;
}

interface RateLimitStatus {
  comments_this_minute: number;
  comments_this_hour: number;
  comments_today: number;
  limit_per_minute: number;
  limit_per_hour: number;
  limit_per_day: number;
}

interface RateLimitResponse {
  success: boolean;
  rate_limit: RateLimitStatus;
  timestamp: string;
}

export function useEventComments() {
  const [comments, setComments] = useState<Comment[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rateLimitStatus, setRateLimitStatus] = useState<RateLimitStatus | null>(
    null
  );

  /**
   * Fetch comments for an event
   */
  const fetchComments = useCallback(
    async (
      eventId: string,
      limit: number = 50,
      offset: number = 0,
      approvedOnly: boolean = true
    ): Promise<CommentsResponse | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          limit: String(limit),
          offset: String(offset),
          approved: String(approvedOnly),
        });

        const response = await fetch(
          `/api/scraper/comments/${eventId}?${params}`
        );
        
        if (!response.ok) {
          const errorData = await response.text();
          throw new Error(errorData || 'Failed to fetch comments');
        }
        
        const data = (await response.json()) as CommentsResponse;

        setComments(data.comments);
        setTotalCount(data.total_count);

        return data;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to fetch comments';
        setError(errorMessage);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Post a new comment
   */
  const postComment = useCallback(
    async (
      eventId: string,
      authorName: string,
      text: string,
      authorEmail?: string
    ): Promise<PostCommentResponse | null> => {
      setIsLoading(true);
      setError(null);

      try {
        // Check rate limit first
        const rateLimitCheck = await checkRateLimit();
        if (
          rateLimitCheck &&
          rateLimitCheck.rate_limit.comments_this_minute >=
            rateLimitCheck.rate_limit.limit_per_minute
        ) {
          const err = new Error(
            'Too many comments. Please wait before posting again.'
          );
          (err as any).rate_limited = true;
          throw err;
        }

        const payload = {
          event_id: eventId,
          author_name: authorName,
          author_email: authorEmail || '',
          text: text,
        };

        const response = await fetch('/api/scraper/comments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || 'Failed to post comment');
        }

        const data = (await response.json()) as PostCommentResponse;

        // Refresh rate limit status
        await checkRateLimit();

        return data;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to post comment';
        setError(errorMessage);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Delete a comment
   */
  const deleteComment = useCallback(
    async (commentId: string): Promise<boolean> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`/api/scraper/comments/${commentId}`, {
          method: 'DELETE',
        });

        if (!response.ok) {
          throw new Error('Failed to delete comment');
        }

        // Remove from local state
        setComments((prev) =>
          prev.filter((c) => c.comment_id !== commentId)
        );

        return true;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to delete comment';
        setError(errorMessage);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Like a comment
   */
  const likeComment = useCallback(
    async (commentId: string): Promise<number | null> => {
      try {
        const response = await fetch(
          `/api/scraper/comments/${commentId}/like`,
          {
            method: 'POST',
          }
        );

        if (!response.ok) {
          throw new Error('Failed to like comment');
        }

        const data = await response.json();

        // Update local state
        setComments((prev) =>
          prev.map((c) =>
            c.comment_id === commentId
              ? { ...c, likes: data.likes }
              : c
          )
        );

        return data.likes;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to like comment';
        setError(errorMessage);
        return null;
      }
    },
    []
  );

  /**
   * Check current rate limit status
   */
  const checkRateLimit = useCallback(async (): Promise<RateLimitResponse | null> => {
    try {
      const response = await fetch('/api/scraper/comments/rate-limit/status');
      
      if (!response.ok) {
        return null;
      }
      
      const data = (await response.json()) as RateLimitResponse;

      if (response.ok) {
        setRateLimitStatus(data.rate_limit);
        return data;
      }

      return null;
    } catch (err) {
      console.error('Error checking rate limit:', err);
      return null;
    }
  }, []);

  /**
   * Load initial rate limit status
   */
  useEffect(() => {
    checkRateLimit();
  }, [checkRateLimit]);

  return {
    comments,
    totalCount,
    isLoading,
    error,
    rateLimitStatus,
    fetchComments,
    postComment,
    deleteComment,
    likeComment,
    checkRateLimit,
  };
}
