"use client";

import { FormEvent, useRef, useState } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  disabled?: boolean;
  busy?: boolean;
  placeholder?: string;
  onSend: (text: string) => Promise<void>;
}

const MAX_LEN = 4000;

export function CoachComposer({
  disabled,
  busy,
  placeholder,
  onSend,
}: Props) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = text.trim();
    if (!value || busy || disabled) return;
    await onSend(value);
    setText("");
    inputRef.current?.focus();
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      // Trigger submit on the parent form.
      const form = (event.target as HTMLTextAreaElement).form;
      form?.requestSubmit();
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 border-t pt-3"
      aria-label="Soạn tin nhắn cho coach"
    >
      <Textarea
        ref={inputRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || busy}
        placeholder={
          placeholder ||
          "Nhập câu hỏi hoặc cảm nghĩ của bạn — Enter để gửi, Shift+Enter để xuống dòng"
        }
        maxLength={MAX_LEN}
        rows={2}
        className="min-h-[60px] resize-none"
        aria-label="Nội dung tin nhắn"
      />
      <Button
        type="submit"
        disabled={disabled || busy || !text.trim()}
        className="gap-1.5 shrink-0"
      >
        <Send className="h-4 w-4" aria-hidden="true" />
        {busy ? "Đang gửi…" : "Gửi"}
      </Button>
    </form>
  );
}
