import { getServerSession } from "next-auth/next";
import { redirect } from "next/navigation";
import { authOptions } from "@/app/api/auth/[...nextauth]/route";

export default async function Dashboard() {
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect('/login');
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-md p-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Welcome, {session.user?.name}!</h1>
        <div className="space-y-4 text-gray-600">
          <p>You've successfully logged in to The Pursuit of Fairness platform.</p>
          <p>Email: {session.user?.email}</p>
          <div className="pt-4">
            <a 
              href="/api/auth/signout" 
              className="text-blue-600 hover:text-blue-800 hover:underline"
            >
              Sign out
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
