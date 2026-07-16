import React, { useState, useEffect, useCallback, useMemo } from 'react';

interface User {
  id: number;
  name: string;
  email: string;
}

interface UserListProps {
  users: User[];
  onSelect: (user: User) => void;
}

export const UserList: React.FC<UserListProps> = ({ users, onSelect }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);

  const filteredUsers = useMemo(() => {
    return users.filter(user => 
      user.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [users, searchTerm]);

  useEffect(() => {
    console.log('UserList mounted');
  }, []);

  const handleSelect = useCallback((user: User) => {
    onSelect(user);
  }, [onSelect]);

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="user-list">
      <input
        type="text"
        placeholder="Search users..."
        value={searchTerm}
        onChange={handleSearch}
      />
      <ul>
        {filteredUsers.map(user => (
          <li key={user.id} onClick={() => handleSelect(user)}>
            {user.name} ({user.email})
          </li>
        ))}
      </ul>
    </div>
  );
};

export default UserList;