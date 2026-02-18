export function normalizePhone(input: string): string {
  const digits = input.replace(/\D/g, "");
  if (digits.startsWith("86") && digits.length === 13) {
    return digits.slice(2);
  }
  return digits;
}

export function isCnPhone(phone: string): boolean {
  return /^1[3-9]\d{9}$/.test(phone);
}

