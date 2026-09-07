export type Request = {
  params: { id: string };
  auth?: { canWrite: boolean };
};

export type Store = {
  read(id: string): Promise<Record<string, unknown> | null>;
};
