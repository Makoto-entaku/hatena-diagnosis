export default function NotFound() {
  return (
    <main className="min-h-screen bg-[#e8eef8] flex items-center justify-center px-4">
      <div className="text-center bg-white rounded-2xl p-10 shadow max-w-sm w-full">
        <p className="text-5xl mb-4">🔍</p>
        <h1 className="text-xl font-bold text-[#1a2e5a] mb-2">
          診断結果が見つかりません
        </h1>
        <p className="text-sm text-[#4a6080]">
          このURLの診断結果は存在しないか、有効期限が切れています。
        </p>
      </div>
    </main>
  );
}
